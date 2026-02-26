import logging
import time
import os
import tempfile
from config import CONVERTER_BOT_TOKEN
from max_client import MaxBotClient
from converter import ImageConverter

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Проверка наличия токена
if not CONVERTER_BOT_TOKEN:
    raise ValueError("No CONVERTER_BOT_TOKEN in .env")

# Создаём клиента MAX
bot = MaxBotClient(CONVERTER_BOT_TOKEN)
BOT_ID = None

# Состояния пользователей: после получения файла ждём выбора формата
# user_state[chat_id] = {'input_path': путь_к_скачанному_файлу}
user_state = {}

# Доступные форматы для разных исходных расширений (пока только изображения)
TARGET_FORMATS = {
    'png': ['jpg', 'webp', 'bmp', 'tiff'],
    'jpg': ['png', 'webp', 'bmp', 'tiff'],
    'jpeg': ['png', 'webp', 'bmp', 'tiff'],
    'gif': ['mp4', 'webm'],  # для gif нужна будет особая обработка, пока заглушка
    'bmp': ['jpg', 'png', 'webp'],
    'webp': ['jpg', 'png'],
    'tiff': ['jpg', 'png'],
}

def get_target_formats(ext):
    """Возвращает список доступных форматов для данного расширения."""
    return TARGET_FORMATS.get(ext.lower(), [])

def handle_update(update):
    global BOT_ID
    update_type = update.get('update_type')
    logger.info(f"Update: {update_type}")

    if update_type == 'message_created':
        msg = update['message']
        # Игнорируем сообщения от самого бота
        if msg['sender'].get('is_bot') and msg['sender'].get('user_id') == BOT_ID:
            return

        # Определяем chat_id
        chat_id = msg['recipient'].get('chat_id') or msg['recipient'].get('user_id')
        user_info = msg['sender']
        # user_id пока не используем, но может пригодиться позже

        # Проверяем наличие вложений (файлов)
        attachments = msg.get('body', {}).get('attachments', [])
        if attachments:
            att = attachments[0]
            # Если это файл, изображение, видео или аудио – пытаемся обработать
            if att['type'] in ['file', 'image', 'video', 'audio']:
                file_token = att['payload'].get('token')
                if file_token:
                    # Здесь в реальности нужно скачать файл по токену.
                    # Пока для теста создаём тестовое изображение.
                    # В дальнейшем заменим на реальное скачивание.
                    temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                    temp_img.close()
                    # Создаём простое красное изображение 100x100
                    from PIL import Image
                    img = Image.new('RGB', (100, 100), color='red')
                    img.save(temp_img.name)
                    input_path = temp_img.name
                    ext = 'png'  # для теста считаем расширение png

                    # Сохраняем путь к файлу в состоянии пользователя
                    user_state[chat_id] = {'input_path': input_path}

                    # Получаем доступные форматы для этого расширения
                    formats = get_target_formats(ext)
                    if not formats:
                        bot.send_message(chat_id, "Для этого типа файла пока нет доступных форматов конвертации.")
                        return

                    # Строим клавиатуру с кнопками выбора формата
                    buttons = []
                    row = []
                    for fmt in formats:
                        row.append({"type": "callback", "text": fmt.upper(), "payload": f"convert_to_{fmt}"})
                        if len(row) == 3:
                            buttons.append(row)
                            row = []
                    if row:
                        buttons.append(row)
                    # Добавляем кнопку отмены
                    buttons.append([{"type": "callback", "text": "❌ Отмена", "payload": "cancel"}])

                    keyboard = {
                        "type": "inline_keyboard",
                        "payload": {"buttons": buttons}
                    }
                    bot.send_message(chat_id, "Выберите целевой формат:", attachments=[keyboard])
                else:
                    bot.send_message(chat_id, "Не удалось получить токен файла.")
            else:
                bot.send_message(chat_id, "Пожалуйста, отправьте файл для конвертации.")
        else:
            # Если нет вложений – обрабатываем текстовые команды
            text = msg.get('body', {}).get('text', '').strip()
            if text == '/start':
                welcome = (
                    "👋 Привет! Я бот для конвертации изображений.\n"
                    "Отправь мне изображение, и я предложу доступные форматы для конвертации."
                )
                bot.send_message(chat_id, welcome)
            else:
                bot.send_message(chat_id, "Отправьте файл с изображением для конвертации или /start")

    elif update_type == 'message_callback':
        callback = update['callback']
        chat_id = callback['message']['recipient']['chat_id']
        payload = callback['payload']

        if payload == 'cancel':
            if chat_id in user_state:
                # Удаляем временный файл, если он есть
                try:
                    os.remove(user_state[chat_id]['input_path'])
                except:
                    pass
                del user_state[chat_id]
            bot.send_message(chat_id, "Операция отменена.")
        elif payload.startswith('convert_to_'):
            target_format = payload.replace('convert_to_', '')
            if chat_id in user_state:
                input_path = user_state[chat_id]['input_path']
                # Показываем, что бот "печатает"
                bot.send_action(chat_id, "typing_on")
                converter = ImageConverter()
                try:
                    # Конвертируем изображение
                    output_path = converter.convert(input_path, target_format)
                    # Загружаем результат в MAX
                    token = bot.upload_file(output_path, 'image')
                    if token:
                        attachment = bot.build_attachment('image', token)
                        bot.send_message(chat_id, f"✅ Конвертация в {target_format.upper()} выполнена!", attachments=[attachment])
                    else:
                        bot.send_message(chat_id, "❌ Не удалось загрузить результат.")
                except Exception as e:
                    logger.error(f"Conversion error: {e}")
                    bot.send_message(chat_id, f"❌ Ошибка при конвертации: {str(e)}")
                finally:
                    # Очищаем временные файлы
                    converter.cleanup()
                    try:
                        os.remove(input_path)
                    except:
                        pass
                    del user_state[chat_id]
            else:
                bot.send_message(chat_id, "Сессия устарела. Отправьте файл заново.")

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
                handle_update(upd)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
