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
        resp = self.session.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()

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

    def upload_file(self, file_path: str, file_type: str) -> Optional[str]:
        """
        Загружает файл в MAX и возвращает токен.
        Упрощённая версия для изображений.
        """
        # Получаем URL для загрузки
        upload_info = self._request("POST", "/uploads", params={"type": file_type})
        upload_url = upload_info["url"]

        # Загружаем файл
        with open(file_path, "rb") as f:
            files = {"data": (file_path, f, "application/octet-stream")}
            resp = requests.post(upload_url, files=files, timeout=60)
            resp.raise_for_status()
            result = resp.json()
            # Для изображений токен обычно лежит в result['token'] или result['photos'][...]['token']
            token = result.get('token')
            if not token and 'photos' in result:
                # Извлекаем токен из структуры photos
                for photo in result['photos'].values():
                    if isinstance(photo, dict) and 'token' in photo:
                        token = photo['token']
                        break
            return token

    def build_attachment(self, file_type: str, token: str) -> Dict:
        return {"type": file_type, "payload": {"token": token}}

    def send_message(
        self,
        chat_id: int,
        text: str,
        attachments: Optional[List[Dict]] = None,
        format: Optional[str] = None,
        disable_link_preview: bool = False,
    ) -> Dict[str, Any]:
        payload = {"text": text, "attachments": attachments or []}
        if format:
            payload["format"] = format
        params = {"chat_id": chat_id, "disable_link_preview": str(disable_link_preview).lower()}
        return self._request("POST", "/messages", params=params, json=payload)
