import os
from dotenv import load_dotenv

load_dotenv()

CONVERTER_BOT_TOKEN = os.getenv('CONVERTER_BOT_TOKEN')
MAX_API_BASE = "https://platform-api.max.ru"
DATABASE_URL = os.getenv('DATABASE_URL')

# Ссылка на бота-навигатор для пополнения баланса
NAVIGATOR_BOT_LINK = os.getenv('NAVIGATOR_BOT_LINK', 'https://max.ru/navigator')
