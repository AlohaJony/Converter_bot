import logging
import time
import os
import tempfile
from config import CONVERTER_BOT_TOKEN
from max_client import MaxBotClient
from converter import ImageConverter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not CONVERTER_BOT_TOKEN:
    raise ValueError("No CONVERTER_BOT_TOKEN in .env")

bot = MaxBotClient(CONVERTER_BOT_TOKEN)
BOT_ID = None

# Состояния пользователей: user_id -> {'input_path': path}
user_state = {}

TARGET_FORMATS = {
    'png': ['jpg', 'webp', 'bmp', 'tiff'],
    'jpg': ['png', 'webp', 'bmp', 'tiff'],
    'jpeg': ['png', 'webp', 'bmp', 'tiff'],
    'gif': ['mp4', 'webm'],
    'bmp': ['jpg', 'png', 'webp'],
    'webp': ['jpg', 'png'],
    'tiff': ['jpg', 'png'],
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
            logger.error("No 'message' field in update")
            return

        sender = msg.get('sender', {})
        # Игнорируем свои сообщения
        if sender.get('is_bot') and sender.get('user_id') == BOT_ID:
            logger.info("Ignoring message from self")
            return

        # ID пользователя, которому будем отвечать
        user_id = sender.get('user_id')
        if not user_id:
            logger.error("No user_id in sender")
            return

        # Проверяем наличие вложений
        attachments = msg.get('body', {}).get('attachments', [])
        if attachments:
            att = attachments[0]
            if att['type'] in ['file', 'image', 'video', 'audio']:
                file_token = att['payload'].get('token')
                if file_token:
                    # ВРЕМЕННО: тестовое изображение
                    temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                    temp_img.close()
                    from PIL import Image
                    img = Image.new('RGB', (100, 100), color='red')
                    img.save(temp_img.name)
                    input_path = temp_img.name
                    ext = 'png'

                    # Сохраняем состояние по user_id
                    user_state[user_id] = {'input_path': input_path}
                    formats = get_target_formats(ext)

                    if not formats:
                        bot.send_message(
                            user_id=user_id,
                            text="Для этого типа файла нет доступных форматов конвертации."
                        )
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
                    bot.send_message(
                        user_id=user_id,
                        text="Выберите целевой формат:",
                        attachments=[keyboard]
                    )
                else:
                    bot.send_message(
                        user_id=user_id,
                        text="Не удалось получить токен файла."
                    )
            else:
                bot.send_message(
                    user_id=user_id,
                    text="Пожалуйста, отправьте файл для конвертации."
                )
        else:
            # Текстовые команды
            text = msg.get('body', {}).get('text', '').strip()
            if text == '/start':
                welcome = (
                    "👋 Привет! Я бот для конвертации изображений.\n"
                    "Отправь мне изображение, и я предложу доступные форматы для конвертации."
                )
                bot.send_message(user_id=user_id, text=welcome)
            else:
                bot.send_message(
                    user_id=user_id,
                    text="Отправьте файл с изображением для конвертации или /start"
                )

    elif update_type == 'message_callback':
        callback = update.get('callback')
        if not callback:
            logger.error("No 'callback' field in update")
            return

        logger.info(f"Callback data: {callback}")

        # В личных сообщениях chat_id = user_id
        user_info = callback.get('user')
        if not user_info:
            logger.error("No user in callback")
            return
        user_id = user_info.get('user_id')
        if not user_id:
            logger.error("No user_id in callback user")
            return

        payload = callback.get('payload')
        logger.info(f"Callback payload: {payload}")

        if payload == 'cancel':
            if user_id in user_state:
                try:
                    os.remove(user_state[user_id]['input_path'])
                except:
                    pass
                del user_state[user_id]
            bot.send_message(user_id=user_id, text="Операция отменена.")
        elif payload and payload.startswith('convert_to_'):
            target_format = payload.replace('convert_to_', '')
            if user_id in user_state:
                input_path = user_state[user_id]['input_path']
                bot.send_action(user_id, "typing_on")
                converter = ImageConverter()
                try:
                    output_path = converter.convert(input_path, target_format)
                    token = bot.upload_file(output_path, 'image')
                    if token:
                        attachment = bot.build_attachment('image', token)
                        bot.send_message(
                            user_id=user_id,
                            text=f"✅ Конвертация в {target_format.upper()} выполнена!",
                            attachments=[attachment]
                        )
                    else:
                        bot.send_message(
                            user_id=user_id,
                            text="❌ Не удалось загрузить результат."
                        )
                except Exception as e:
                    logger.error(f"Conversion error: {e}")
                    bot.send_message(
                        user_id=user_id,
                        text=f"❌ Ошибка при конвертации: {str(e)}"
                    )
                finally:
                    converter.cleanup()
                    try:
                        os.remove(input_path)
                    except:
                        pass
                    del user_state[user_id]
            else:
                bot.send_message(
                    user_id=user_id,
                    text="Сессия устарела. Отправьте файл заново."
                )
        else:
            bot.send_message(
                user_id=user_id,
                text="Неизвестная команда."
            )
    else:
        logger.warning(f"Unknown update type: {update_type}")

def main():
    global BOT_ID
    logger.info("Starting Converter Bot (images only, test mode)...")
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
