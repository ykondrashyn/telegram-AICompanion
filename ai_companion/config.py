import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
XAI_API_KEY = os.environ.get("XAI_API_KEY")
YT_API_KEY = os.environ.get("YT_API_KEY", "")
DB_FILENAME = os.environ.get("DB_FILENAME", "bot_database.db")
DEFAULT_AI_MODE = os.environ.get("DEFAULT_AI_MODE", "grok").lower()
