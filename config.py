import os
from dotenv import load_dotenv

load_dotenv()

CONVERTER_BOT_TOKEN = os.getenv('CONVERTER_BOT_TOKEN')
MAX_API_BASE = "https://platform-api.max.ru"
