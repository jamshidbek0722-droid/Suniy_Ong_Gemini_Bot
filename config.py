import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing in environment variables or .env file!")

try:
    ADMIN_ID = int(os.getenv("ADMIN_ID"))
except (TypeError, ValueError):
    raise ValueError("ADMIN_ID is missing or not a valid integer in environment variables or .env file!")

try:
    DATABASE_CHANNEL_ID = int(os.getenv("DATABASE_CHANNEL_ID"))
except (TypeError, ValueError):
    raise ValueError("DATABASE_CHANNEL_ID is missing or not a valid integer in environment variables or .env file!")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY is missing in environment variables or .env file!")

# Dedicated list of channels for forced subscription checking.
# This list is independent of the secret DATABASE_CHANNEL_ID.
REQUIRED_CHANNELS = [
    {
        "id": "@ai_news_uzbekistan",  # Channel ID or username (with @)
        "name": "Sun'iy Ong Yangiliklari",
        "url": "https://t.me/ai_news_uzbekistan"
    }
]

