import requests
import logging
from typing import Optional, Dict, Any, List
from config import MAX_API_BASE

logger = logging.getLogger(__name__)

class MaxBotClient:
    def __init__(self, token: str):
        self.token = token
        self.base_url = MAX_API_BASE
        self.session = requests.Session()
        self.session.headers.update({"Authorization": token})

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        logger.info(f"Request: {method} {url} {kwargs.get('params')} {kwargs.get('json')}")
        resp = self.session.request(method, url, **kwargs)
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            logger.error(f"HTTP error {resp.status_code} for {method} {path}: {resp.text}")
            raise
        return resp.json()

    def answer_callback(self, callback_id: str, text: Optional[str] = None) -> Dict[str, Any]:
        payload = {}
        if text:
            payload['notification'] = text
        return self._request("POST", "/answers", params={'callback_id': callback_id}, json=payload)

    def get_me(self) -> Dict[str, Any]:
        return self._request("GET", "/me")

    def get_updates(self, marker: Optional[int] = None, timeout: int = 30, limit: int = 100) -> Dict[str, Any]:
        params = {"timeout": timeout, "limit": limit}
        if marker:
            params["marker"] = marker
        return self._request("GET", "/updates", params=params)

    def send_action(self, chat_id: int, action: str) -> bool:
        path = f"/chats/{chat_id}/actions"
        resp = self._request("POST", path, json={"action": action})
        return resp.get("success", False)

    def get_message(self, message_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/messages/{message_id}")

    def edit_message(
        self,
        message_id: str,
        text: str,
        user_id: Optional[int] = None,
        chat_id: Optional[int] = None,
        attachments: Optional[List[Dict]] = None,
        format: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Редактирует сообщение (можно убрать клавиатуру)."""
        if not (user_id or chat_id):
            raise ValueError("Either user_id or chat_id must be provided")
        payload = {"text": text, "attachments": attachments or []}
        if format:
            payload["format"] = format
        params = {}
        if user_id:
            params["user_id"] = user_id
        if chat_id:
            params["chat_id"] = chat_id
        return self._request("PUT", f"/messages?message_id={message_id}", params=params, json=payload)

    def upload_file(self, file_path: str, file_type: str) -> Optional[str]:
        upload_info = self._request("POST", "/uploads", params={"type": file_type})
        upload_url = upload_info["url"]

        with open(file_path, "rb") as f:
            files = {"data": (file_path, f, "application/octet-stream")}
            resp = requests.post(upload_url, files=files, timeout=60)
            try:
                resp.raise_for_status()
            except requests.HTTPError as e:
                logger.error(f"CDN upload failed: {resp.status_code} - {resp.text[:200]}")
                raise
            try:
                result = resp.json()
            except ValueError as e:
                logger.error(f"CDN response not JSON: {resp.text[:200]}")
                raise
            token = result.get('token')
            if not token and 'photos' in result:
                for photo in result['photos'].values():
                    if isinstance(photo, dict) and 'token' in photo:
                        token = photo['token']
                        break
            return token

    def build_attachment(self, file_type: str, token: str) -> Dict:
        return {"type": file_type, "payload": {"token": token}}

    def send_message(
        self,
        text: str,
        user_id: Optional[int] = None,
        chat_id: Optional[int] = None,
        attachments: Optional[List[Dict]] = None,
        format: Optional[str] = None,
        disable_link_preview: bool = False,
    ) -> Dict[str, Any]:
        if not (user_id or chat_id):
            raise ValueError("Either user_id or chat_id must be provided")
        payload = {"text": text, "attachments": attachments or []}
        if format:
            payload["format"] = format
        params = {"disable_link_preview": str(disable_link_preview).lower()}
        if user_id:
            params["user_id"] = user_id
        if chat_id:
            params["chat_id"] = chat_id
        return self._request("POST", "/messages", params=params, json=payload)
