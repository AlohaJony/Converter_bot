import logging
import time
import os
import tempfile
import requests
import re
import subprocess
import json
from config import CONVERTER_BOT_TOKEN, NAVIGATOR_BOT_LINK
from max_client import MaxBotClient
from user_manager import (
    get_or_create_user, get_balance, deduct_tokens,
    check_and_use_free_limit, get_price
)
from file_converter import FileConverter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not CONVERTER_BOT_TOKEN:
    raise ValueError("No CONVERTER_BOT_TOKEN in .env")

bot = MaxBotClient(CONVERTER_BOT_TOKEN)
BOT_ID = None

# Кэш загруженных файлов
file_cache = {}
CACHE_TTL = 600  # 10 минут

TARGET_FORMATS = {
    'png': ['jpg', 'webp', 'bmp', 'tiff'],
    'jpg': ['png', 'webp', 'bmp', 'tiff'],
    'jpeg': ['png', 'webp', 'bmp', 'tiff'],
    'gif': ['mp4', 'webm'],
    'bmp': ['jpg', 'png', 'webp', 'tiff'],
    'webp': ['jpg', 'png', 'bmp', 'tiff'],
    'tiff': ['jpg', 'png', 'webp', 'bmp'],
    'mp3': ['wav', 'ogg', 'flac', 'aac', 'm4a'],
    'wav': ['mp3', 'ogg', 'flac', 'aac', 'm4a'],
    'ogg': ['mp3', 'wav', 'flac', 'aac', 'm4a'],
    'flac': ['mp3', 'wav', 'ogg', 'aac', 'm4a'],
    'aac': ['mp3', 'wav', 'ogg', 'flac', 'm4a'],
    'm4a': ['mp3', 'wav', 'ogg', 'flac', 'aac'],
    'mp4': ['avi', 'mkv', 'mov', 'webm', 'gif'],
    'avi': ['mp4', 'mkv', 'mov', 'webm', 'gif'],
    'mkv': ['mp4', 'avi', 'mov', 'webm', 'gif'],
    'mov': ['mp4', 'avi', 'mkv', 'webm', 'gif'],
    'webm': ['mp4', 'avi', 'mkv', 'mov', 'gif'],
    'doc': ['pdf', 'docx', 'odt', 'txt', 'rtf'],
    'docx': ['pdf', 'doc', 'odt', 'txt', 'rtf'],
    'odt': ['pdf', 'doc', 'docx', 'txt', 'rtf'],
    'pdf': ['docx', 'jpg', 'png', 'txt'],
    'txt': ['pdf', 'doc', 'docx', 'rtf'],
    'rtf': ['pdf', 'doc', 'docx', 'txt'],
    'zip': ['7z', 'tar', 'gz'],
    'rar': ['zip', '7z'],
}

def get_target_formats(ext):
    return TARGET_FORMATS.get(ext.lower(), [])

def handle_update(update):
    global BOT_ID
    update_type = update.get('update_type')
    logger.info(f"Update type: {update_type}")

    if update_type == 'message_created':
        msg = update.get('message')
        if not msg:
            logger.error("No 'message' in update")
            return

        sender = msg.get('sender', {})
        if sender.get('is_bot') and sender.get('user_id') == BOT_ID:
            logger.info("Ignoring own message")
            return

        user_id = sender.get('user_id')
        if not user_id:
            logger.error("No user_id in sender")
            return

        username = sender.get('username')
        first_name = sender.get('first_name')
        get_or_create_user(user_id, username, first_name)

        text = msg.get('body', {}).get('text', '').strip()
        logger.info(f"Message from user {user_id}: {text}")

        attachments = msg.get('body', {}).get('attachments', [])
        if attachments:
            att = attachments[0]
            att_type = att.get('type', '')
            logger.info(f"Attachment type: {att_type}, full payload: {att.get('payload')}")

            if att_type in ['file', 'image', 'video', 'audio']:
                file_token = att['payload'].get('token')
                if not file_token:
                    bot.send_message(user_id=user_id, text="Не удалось получить токен файла.")
                    return

                file_name = att.get('payload', {}).get('name', '')
                mime_type = att.get('payload', {}).get('mime_type', '')
                file_url = att.get('payload', {}).get('url', '')
                mid = msg.get('body', {}).get('mid')
                logger.info(f"File info - name: {file_name}, mime: {mime_type}, url: {file_url}")

                # Проверяем кэш
                cached = file_cache.get(user_id)
                if cached and cached.get('mid') == mid:
                    ext = cached['ext']
                    logger.info(f"Using cached file for user {user_id}, ext: {ext}")
                else:
                    # ---- Попытки определить расширение до скачивания ----
                    ext = None
                    # 1. Из имени файла
                    if file_name:
                        ext = os.path.splitext(file_name)[1].lower().lstrip('.')
                        if ext:
                            logger.info(f"Extension from filename: {ext}")

                    # 2. Из mime-типа
                    if not ext and mime_type:
                        mime_to_ext = {
                            'image/jpeg': 'jpg',
                            'image/png': 'png',
                            'image/gif': 'gif',
                            'image/webp': 'webp',
                            'image/bmp': 'bmp',
                            'image/tiff': 'tiff',
                            'audio/mpeg': 'mp3',
                            'audio/wav': 'wav',
                            'audio/ogg': 'ogg',
                            'audio/flac': 'flac',
                            'audio/aac': 'aac',
                            'audio/mp4': 'm4a',
                            'video/mp4': 'mp4',
                            'video/x-msvideo': 'avi',
                            'video/x-matroska': 'mkv',
                            'video/webm': 'webm',
                            'video/quicktime': 'mov',
                            'application/pdf': 'pdf',
                            'application/msword': 'doc',
                            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
                            'application/vnd.oasis.opendocument.text': 'odt',
                            'text/plain': 'txt',
                            'application/rtf': 'rtf',
                            'application/zip': 'zip',
                            'application/x-rar-compressed': 'rar',
                        }
                        ext = mime_to_ext.get(mime_type)
                        if ext:
                            logger.info(f"Extension from mime: {ext}")

                    # 3. Из URL (путь)
                    if not ext and file_url:
                        url_path = file_url.split('?')[0]
                        possible_ext = os.path.splitext(url_path)[1].lower().lstrip('.')
                        if possible_ext and len(possible_ext) < 10:
                            ext = possible_ext
                            logger.info(f"Extension from URL path: {ext}")
                        else:
                            match = re.search(r'\.([a-zA-Z0-9]{2,4})(?:\?|$)', file_url)
                            if match:
                                ext = match.group(1).lower()
                                logger.info(f"Extension from URL regex: {ext}")

                    # 4. HEAD-запрос
                    if not ext and file_url:
                        try:
                            head_resp = requests.head(file_url, timeout=5, allow_redirects=True)
                            cd = head_resp.headers.get('content-disposition', '')
                            if 'filename=' in cd:
                                fname_match = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';]+)["\']?', cd)
                                if fname_match:
                                    fname = fname_match.group(1)
                                    ext = os.path.splitext(fname)[1].lower().lstrip('.')
                                    logger.info(f"Extension from Content-Disposition: {ext}")
                            if not ext:
                                ct = head_resp.headers.get('content-type', '').split(';')[0].strip()
                                ct_to_ext = {
                                    'image/jpeg': 'jpg',
                                    'image/png': 'png',
                                    'image/gif': 'gif',
                                    'image/webp': 'webp',
                                    'image/bmp': 'bmp',
                                    'image/tiff': 'tiff',
                                    'audio/mpeg': 'mp3',
                                    'audio/wav': 'wav',
                                    'audio/ogg': 'ogg',
                                    'audio/flac': 'flac',
                                    'video/mp4': 'mp4',
                                    'video/x-msvideo': 'avi',
                                    'video/webm': 'webm',
                                    'video/quicktime': 'mov',
                                    'application/pdf': 'pdf',
                                    'application/msword': 'doc',
                                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
                                    'text/plain': 'txt',
                                }
                                ext = ct_to_ext.get(ct)
                                if ext:
                                    logger.info(f"Extension from HEAD Content-Type: {ext}")
                        except Exception as e:
                            logger.warning(f"HEAD request failed: {e}")

                    # 5. По типу вложения
                    if not ext and att_type:
                        if att_type == 'image':
                            ext = 'jpg'
                            logger.info("Fallback to jpg for image type")
                        elif att_type == 'video':
                            ext = 'mp4'
                            logger.info("Fallback to mp4 for video type")
                        elif att_type == 'audio':
                            ext = 'mp3'
                            logger.info("Fallback to mp3 for audio type")

                    # ---- Если всё ещё не определили, скачиваем и анализируем содержимое ----
                    if not ext:
                        try:
                            logger.info(f"No extension detected before download, downloading file for content analysis")
                            resp = requests.get(file_url, stream=True, timeout=30)
                            resp.raise_for_status()
                            temp_file = tempfile.NamedTemporaryFile(delete=False)
                            temp_path = temp_file.name
                            temp_file.close()
                            with open(temp_path, 'wb') as f:
                                for chunk in resp.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            logger.info(f"File downloaded to {temp_path} for type detection")

                            # Попытка определить тип через PIL (изображения)
                            try:
                                from PIL import Image
                                with Image.open(temp_path) as img:
                                    fmt = img.format
                                    if fmt:
                                        pil_to_ext = {
                                            'JPEG': 'jpg',
                                            'PNG': 'png',
                                            'GIF': 'gif',
                                            'BMP': 'bmp',
                                            'TIFF': 'tiff',
                                            'WEBP': 'webp',
                                        }
                                        ext = pil_to_ext.get(fmt)
                                        if ext:
                                            logger.info(f"Extension detected from PIL: {ext}")
                            except Exception:
                                pass

                            # Попытка через ffprobe (аудио/видео)
                            if not ext:
                                try:
                                    result = subprocess.run(
                                        ['ffprobe', '-v', 'quiet', '-show_format', '-print_format', 'json', temp_path],
                                        capture_output=True, text=True, timeout=10
                                    )
                                    if result.returncode == 0:
                                        data = json.loads(result.stdout)
                                        format_name = data.get('format', {}).get('format_name', '').lower()
                                        # Простейший маппинг (можно расширить)
                                        if 'mp3' in format_name:
                                            ext = 'mp3'
                                        elif 'mp4' in format_name or 'mov' in format_name:
                                            ext = 'mp4'
                                        elif 'matroska' in format_name:
                                            ext = 'mkv'
                                        elif 'avi' in format_name:
                                            ext = 'avi'
                                        elif 'wav' in format_name:
                                            ext = 'wav'
                                        elif 'flac' in format_name:
                                            ext = 'flac'
                                        elif 'ogg' in format_name:
                                            ext = 'ogg'
                                        if ext:
                                            logger.info(f"Extension detected from ffprobe: {ext}")
                                except Exception as e:
                                    logger.warning(f"ffprobe failed: {e}")

                            if not ext:
                                # Не удалось определить даже после скачивания
                                os.remove(temp_path)
                                bot.send_message(user_id=user_id, text="Не удалось определить формат файла. Попробуйте другой файл.")
                                return

                            # Переименовываем файл с правильным расширением
                            new_path = temp_path + '.' + ext
                            os.rename(temp_path, new_path)
                            temp_path = new_path

                            # Сохраняем в кэш
                            file_cache[user_id] = {
                                'path': temp_path,
                                'ext': ext,
                                'mid': mid,
                                'timestamp': time.time()
                            }
                            logger.info(f"Cached file for user {user_id} with detected ext {ext}")

                        except Exception as e:
                            logger.error(f"Download/content analysis failed: {e}")
                            bot.send_message(user_id=user_id, text="❌ Не удалось обработать файл.")
                            return
                    else:
                        # Если расширение определено до скачивания, скачиваем обычным порядком
                        try:
                            resp = requests.get(file_url, stream=True, timeout=30)
                            resp.raise_for_status()
                            suffix = f".{ext}"
                            temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
                            temp_path = temp_file.name
                            temp_file.close()
                            with open(temp_path, 'wb') as f:
                                for chunk in resp.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            logger.info(f"File downloaded to {temp_path}")
                        except Exception as e:
                            logger.error(f"Download failed: {e}")
                            bot.send_message(user_id=user_id, text="❌ Не удалось скачать файл.")
                            return

                        # Сохраняем в кэш
                        file_cache[user_id] = {
                            'path': temp_path,
                            'ext': ext,
                            'mid': mid,
                            'timestamp': time.time()
                        }
                        logger.info(f"Cached file for user {user_id}")

                # После того как файл есть в кэше (или был), получаем доступные форматы
                formats = get_target_formats(ext)
                if not formats:
                    bot.send_message(user_id=user_id, text="Для этого типа файла пока нет доступных форматов конвертации.")
                    return

                # Строим клавиатуру
                buttons = []
                row = []
                for fmt in formats:
                    row.append({"type": "callback", "text": fmt.upper(), "payload": f"convert_to_{fmt}"})
                    if len(row) == 3:
                        buttons.append(row)
                        row = []
                if row:
                    buttons.append(row)
                buttons.append([{"type": "callback", "text": "❌ Отмена", "payload": "cancel"}])

                keyboard = {
                    "type": "inline_keyboard",
                    "payload": {"buttons": buttons}
                }
                bot.send_message(user_id=user_id, text="Выберите целевой формат:", attachments=[keyboard])
            else:
                bot.send_message(user_id=user_id, text="Пожалуйста, отправьте файл для конвертации.")
        else:
            # Текстовые сообщения
            if text == '/start':
                balance = get_balance(user_id)
                welcome = (
                    f"👋 Привет! Я бот для конвертации файлов.\n"
                    f"У вас {balance} токенов. Бесплатно: 10 конвертаций в день, далее 2 токена за операцию.\n\n"
                    f"Отправьте мне файл, и я предложу доступные форматы."
                )
                bot.send_message(user_id=user_id, text=welcome)
            else:
                bot.send_message(user_id=user_id, text="Отправьте файл для конвертации или /start")

    elif update_type == 'message_callback':
        callback = update.get('callback')
        if not callback:
            logger.error("No 'callback' in update")
            return

        callback_id = callback.get('callback_id')
        if not callback_id:
            logger.error("No callback_id in callback")
            return

        user_info = callback.get('user')
        if not user_info:
            logger.error("No user in callback")
            return
        user_id = user_info.get('user_id')
        if not user_id:
            logger.error("No user_id in callback")
            return

        payload = callback.get('payload')
        logger.info(f"Callback payload: {payload}")

        # Подтверждаем callback
        try:
            bot.answer_callback(callback_id, text="⏳ Обрабатываю...")
        except Exception as e:
            logger.error(f"Failed to answer callback: {e}")

        if payload == 'cancel':
            if user_id in file_cache:
                # Можно удалить кэш, но не обязательно
                pass
            bot.send_message(user_id=user_id, text="Операция отменена.")
        elif payload.startswith('convert_to_'):
            target_format = payload.replace('convert_to_', '')
            cached = file_cache.get(user_id)
            if not cached or time.time() - cached['timestamp'] > CACHE_TTL:
                bot.send_message(user_id=user_id, text="Сессия устарела. Отправьте файл заново.")
                return

            ext = cached['ext']
            file_path = cached['path']
            mid = cached['mid']

            # Проверка лимитов
            price = get_price('converter')
            if check_and_use_free_limit(user_id, 'converter'):
                logger.info(f"User {user_id} uses free conversion")
                process_conversion(user_id, target_format, ext, file_path, mid, free=True)
            else:
                balance = get_balance(user_id)
                if balance >= price:
                    if deduct_tokens(user_id, price, f"Конвертация в {target_format}"):
                        process_conversion(user_id, target_format, ext, file_path, mid, free=False)
                    else:
                        bot.send_message(user_id=user_id, text="❌ Ошибка списания токенов.")
                else:
                    keyboard = {
                        "type": "inline_keyboard",
                        "payload": {
                            "buttons": [[
                                {"type": "link", "text": "💳 Пополнить баланс", "url": NAVIGATOR_BOT_LINK}
                            ]]
                        }
                    }
                    bot.send_message(
                        user_id=user_id,
                        text=f"❌ Недостаточно токенов. Стоимость: {price} токенов. Ваш баланс: {balance}.",
                        attachments=[keyboard]
                    )
        else:
            bot.send_message(user_id=user_id, text="Неизвестная команда.")
    else:
        logger.warning(f"Unknown update type: {update_type}")

def process_conversion(user_id, target_format, ext, input_path, mid, free=False):
    try:
        bot.edit_message(
            message_id=mid,
            text="⏳ Обрабатываю ваш файл...",
            user_id=user_id
        )
        logger.info(f"Edited message {mid} for user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to edit message: {e}")

    bot.send_action(user_id, "typing_on")

    converter = FileConverter()
    output_path = None
    try:
        output_path = converter.convert(input_path, target_format)
        logger.info(f"Converted to {output_path}")

        tgt_ext = target_format.lower()
        if tgt_ext in ['jpg','jpeg','png','gif','bmp','webp','tiff']:
            file_type = 'file'
        elif tgt_ext in ['mp3','wav','ogg','flac','aac','m4a']:
            file_type = 'audio'
        elif tgt_ext in ['mp4','avi','mkv','mov','webm']:
            file_type = 'video'
        else:
            file_type = 'file'
        logger.info(f"Detected file_type: {file_type}")

        token = bot.upload_file(output_path, file_type)
        if token:
            attachment = bot.build_attachment(file_type, token)
            caption = f"✅ Конвертация в {target_format.upper()} выполнена!"
            if not free:
                caption += f"\n(списано {get_price('converter')} токенов)"
            bot.send_message(user_id=user_id, text=caption, attachments=[attachment])
            logger.info(f"Result sent to user {user_id}")
        else:
            bot.send_message(user_id=user_id, text="❌ Не удалось загрузить результат.")
            logger.error("Upload returned no token")
    except Exception as e:
        logger.error(f"Conversion error: {e}", exc_info=True)
        bot.send_message(user_id=user_id, text=f"❌ Ошибка при конвертации: {str(e)}")
    finally:
        converter.cleanup()
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception as e:
                logger.warning(f"Failed to remove temp file {output_path}: {e}")

def main():
    global BOT_ID
    logger.info("Starting Converter Bot...")
    try:
        me = bot.get_me()
        BOT_ID = me['user_id']
        logger.info(f"Bot ID: {BOT_ID}, username: @{me.get('username')}")
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")
        return

    marker = None
    while True:
        try:
            updates_data = bot.get_updates(marker=marker, timeout=30)
            updates = updates_data.get('updates', [])
            new_marker = updates_data.get('marker')
            if new_marker is not None:
                marker = new_marker
                logger.info(f"Marker updated to {marker}")
            for upd in updates:
                try:
                    handle_update(upd)
                except Exception as e:
                    logger.error(f"Error handling update: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
