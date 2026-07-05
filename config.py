import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing in environment variables!")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing in environment variables!")

# Parse DB_CHANNEL_ID
db_channel = os.getenv("DB_CHANNEL_ID")
if not db_channel:
    raise ValueError("DB_CHANNEL_ID is missing in environment variables!")
try:
    DB_CHANNEL_ID = int(db_channel)
except ValueError:
    raise ValueError("DB_CHANNEL_ID must be a valid integer!")

# Parse OWNER_ID
owner = os.getenv("OWNER_ID")
if not owner:
    raise ValueError("OWNER_ID is missing in environment variables!")
try:
    OWNER_ID = int(owner)
except ValueError:
    raise ValueError("OWNER_ID must be a valid integer!")

# Aliases for backward compatibility in internal modules
ADMIN_ID = OWNER_ID
DATABASE_CHANNEL_ID = DB_CHANNEL_ID

# MongoDB connection string
MONGO_URI = os.getenv("MONGO_URI") or os.getenv("MONGO_URL") or "mongodb://localhost:27017/"

# Dedicated list of channels for forced subscription checking.
REQUIRED_CHANNELS = [
    {
        "id": "@ai_news_uzbekistan",
        "name": "Sun'iy Ong Yangiliklari",
        "url": "https://t.me/ai_news_uzbekistan"
    }
]
