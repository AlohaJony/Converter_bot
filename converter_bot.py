import logging
import time
import os
import tempfile
import requests
import re
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

# Кэш файлов (user_id -> данные)
file_cache = {}
CACHE_TTL = 600

# (оставьте здесь функцию очистки кэша, если она у вас есть)

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
        # Проверяем наличие message
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

        # Логируем текст сообщения для диагностики
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
                    # Скачиваем файл
                    if not file_url:
                        bot.send_message(user_id=user_id, text="Не удалось получить URL файла.")
                        return

                    # Определяем расширение (как раньше)
                    ext = None
                    # ... (вставьте сюда вашу логику определения расширения)
                    # Для краткости я пропущу, но у вас она должна быть.
                    # Если её нет, добавьте, иначе бот не поймёт формат.
                    # Простейший вариант:
                    if file_name:
                        ext = os.path.splitext(file_name)[1].lower().lstrip('.')
                    if not ext and mime_type:
                        mime_to_ext = {
                            'image/jpeg': 'jpg',
                            'image/png': 'png',
                            # ... и т.д.
                        }
                        ext = mime_to_ext.get(mime_type)
                    if not ext:
                        logger.warning(f"Could not determine extension for user {user_id}")
                        bot.send_message(user_id=user_id, text="Не удалось определить формат файла.")
                        return

                    # Скачиваем файл
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

                formats = get_target_formats(ext)
                if not formats:
                    bot.send_message(user_id=user_id, text="Для этого типа файла нет доступных форматов конвертации.")
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
            # Текстовые команды
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
                # можно удалить кэш
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

            # Проверка лимитов (аналогично вашему коду)
            price = get_price('converter')
            if check_and_use_free_limit(user_id, 'converter'):
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
    # Функция конвертации – должна быть у вас
    # (я опускаю для краткости, но она у вас есть)
    pass

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
