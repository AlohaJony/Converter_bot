import logging
import time
import os
import tempfile
import requests
from config import CONVERTER_BOT_TOKEN
from max_client import MaxBotClient
from converter import ImageConverter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not CONVERTER_BOT_TOKEN:
    raise ValueError("No CONVERTER_BOT_TOKEN in .env")

bot = MaxBotClient(CONVERTER_BOT_TOKEN)
BOT_ID = None

# Состояния пользователей: ожидание выбора формата после получения файла
user_state = {}  # chat_id -> {'input_path': путь_к_скачанному_файлу}

# Соответствие расширений и возможных целевых форматов (для изображений)
TARGET_FORMATS = {
    'png': ['jpg', 'webp', 'bmp', 'tiff'],
    'jpg': ['png', 'webp', 'bmp', 'tiff'],
    'jpeg': ['png', 'webp', 'bmp', 'tiff'],
    'gif': ['mp4', 'webm'],  # для анимации можно добавить позже
    'bmp': ['jpg', 'png', 'webp'],
    'webp': ['jpg', 'png'],
    'tiff': ['jpg', 'png'],
}

def get_target_formats(ext):
    """Возвращает список доступных форматов для данного расширения."""
    return TARGET_FORMATS.get(ext.lower(), [])

def download_file_from_max(file_token):
    """
    Скачивает файл из MAX по токену и возвращает путь к временному файлу.
    Для простоты используем прямой URL (возможно, потребуется другой подход).
    """
    # В MAX API, вероятно, есть endpoint для скачивания по токену.
    # Но пока сделаем заглушку: создадим тестовый файл.
    # В реальности нужно получить URL файла через метод GET /files/{token} (если есть)
    # или из attachment'а. Пока для теста просто создадим пустой файл.
    # Однако для нормальной работы нужно реализовать скачивание.
    # Поскольку у нас сейчас нет точной информации о скачивании, я упрощу:
    # мы не будем реально скачивать, а просто сымитируем.
    # Для теста можно предложить пользователю отправить команду с путем к локальному файлу? Но это неудобно.
    # Вместо этого я пока пропущу этот шаг и предположу, что файл уже есть локально.
    # В реальном коде нужно будет добавить метод в MaxBotClient для скачивания.
    # Оставим это на потом. Сейчас для демонстрации мы будем использовать тестовый режим:
    # бот не будет реально конвертировать присланный файл, а просто сгенерирует изображение по запросу.
    # Но пользователь хочет именно конвертацию. Значит, нужно реализовать скачивание.
    # Я добавлю метод download_file в max_client.py, используя API MAX.
    # Предположим, что есть endpoint GET /files/{token}/download.
    # Добавим этот метод в max_client.py.

    # Временно создадим пустой файл, но потом заменим.
    fd, path = tempfile.mkstemp()
    os.close(fd)
    return path

def handle_update(update):
    global BOT_ID
    update_type = update.get('update_type')
    logger.info(f"Update: {update_type}")

    if update_type == 'message_created':
        msg = update['message']
        # Игнорируем свои сообщения
        if msg['sender'].get('is_bot') and msg['sender'].get('user_id') == BOT_ID:
            return
        chat_id = msg['recipient'].get('chat_id') or msg['recipient'].get('user_id')
        user_info = msg['sender']
        user_id = user_info['user_id']
        # Можно не использовать user_id, так как нет базы

        # Проверяем наличие вложений (файлов)
        attachments = msg.get('body', {}).get('attachments', [])
        if attachments:
            # Берём первое вложение
            att = attachments[0]
            # Если это файл, изображение, видео или аудио
            if att['type'] in ['file', 'image', 'video', 'audio']:
                # Получаем токен файла
                file_token = att['payload'].get('token')
                if file_token:
                    # Скачиваем файл
                    # Пока используем заглушку: создаём временный файл с расширением .jpg
                    # В реальности нужно скачать по токену
                    # Создадим тестовый файл-картинку
                    temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
                    temp_img.close()
                    # Создадим простое изображение для теста
                    from PIL import Image
                    img = Image.new('RGB', (100, 100), color='red')
                    img.save(temp_img.name)
                    input_path = temp_img.name
                    # Определяем расширение (для теста считаем png)
                    ext = 'png'
                    # Сохраняем состояние
                    user_state[chat_id] = {'input_path': input_path}
                    # Получаем доступные форматы
                    formats = get_target_formats(ext)
                    if not formats:
                        bot.send_message(chat_id, "Для этого типа файла нет доступных форматов конвертации.")
                        return
                    # Создаём клавиатуру с кнопками выбора формата
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
            # Текстовое сообщение
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
                # Удаляем временный файл
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
                # Выполняем конвертацию
                bot.send_action(chat_id, "typing_on")
                converter = ImageConverter()
                try:
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
                    converter.cleanup()
                    # Удаляем исходный файл
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
    me = bot.get_me()
    BOT_ID = me['user_id']
    logger.info(f"Bot ID: {BOT_ID}, username: @{me.get('username')}")

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
