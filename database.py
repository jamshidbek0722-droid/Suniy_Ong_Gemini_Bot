import json
import logging
from datetime import datetime
from aiogram import Bot
from aiogram.types import BufferedInputFile, InputMediaDocument
import config

logger = logging.getLogger(__name__)

class DBManager:
    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        self.pinned_msg_id = None
        self.cache = {
            "users": {},
            "config": {
                "global_footer": ""
            }
        }

    async def initialize(self, bot: Bot):
        """
        Loads index.json from the pinned message in the channel database.
        If not found, creates and pins a new index.json file.
        """
        try:
            logger.info("Initializing database from Telegram channel...")
            chat = await bot.get_chat(chat_id=self.channel_id)
            pinned_msg = chat.pinned_message
            
            if pinned_msg and pinned_msg.document and pinned_msg.document.file_name == "index.json":
                file_id = pinned_msg.document.file_id
                file = await bot.get_file(file_id)
                
                # Download into memory buffer
                result = await bot.download(file)
                file_bytes = result.read()
                
                self.cache = json.loads(file_bytes.decode('utf-8'))
                self.pinned_msg_id = pinned_msg.message_id
                logger.info(f"Database successfully loaded from Telegram. Total users in cache: {len(self.cache.get('users', {}))}")
            else:
                logger.warning("No pinned database index.json found. Creating a new one...")
                await self._create_new_db(bot)
        except Exception as e:
            logger.error(f"Error during database initialization: {e}")
            logger.warning("Attempting to create and pin a new database file as fallback...")
            await self._create_new_db(bot)

    async def _create_new_db(self, bot: Bot):
        try:
            data_bytes = json.dumps(self.cache, indent=2).encode('utf-8')
            sent_msg = await bot.send_document(
                chat_id=self.channel_id,
                document=BufferedInputFile(data_bytes, filename="index.json"),
                caption="Sun'iy Ong Gemini Bot Pinned Database"
            )
            # Pin the sent message
            await bot.pin_chat_message(chat_id=self.channel_id, message_id=sent_msg.message_id)
            self.pinned_msg_id = sent_msg.message_id
            logger.info(f"Created and pinned new database index.json with message ID {self.pinned_msg_id}")
        except Exception as e:
            logger.critical(f"Failed to create new database on Telegram channel: {e}")
            # Setup fallback message ID to prevent crash
            self.pinned_msg_id = 999999999

    async def save(self, bot: Bot) -> bool:
        """
        Syncs the current RAM cache back to the channel database
        by editing the existing pinned message document media.
        """
        if not self.pinned_msg_id or self.pinned_msg_id == 999999999:
            logger.error("Cannot sync database: Pinned message ID is not set.")
            return False
        try:
            data_bytes = json.dumps(self.cache, indent=2).encode('utf-8')
            await bot.edit_message_media(
                chat_id=self.channel_id,
                message_id=self.pinned_msg_id,
                media=InputMediaDocument(
                    media=BufferedInputFile(data_bytes, filename="index.json"),
                    caption=f"Sun'iy Ong Gemini Bot Pinned Database (Synced: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
                )
            )
            logger.info("Database synced to Telegram channel successfully.")
            return True
        except Exception as e:
            logger.error(f"Error syncing database to Telegram channel: {e}")
            return False

    # In-memory CRUD operations
    def register_user(self, user_id: int, username: str = None) -> bool:
        """
        Registers a user if they are not already in the database cache.
        Returns True if newly registered, False otherwise.
        """
        uid_str = str(user_id)
        if uid_str not in self.cache["users"]:
            self.cache["users"][uid_str] = {
                "id": user_id,
                "username": username,
                "tokens_used": 0,
                "messages_sent": 0,
                "join_date": datetime.now().strftime("%Y-%m-%d"),
                "profile": {
                    "completed": False,
                    "gender": None,
                    "age": None,
                    "region": None,
                    "interest": None
                }
            }
            return True
        else:
            # Update username if it has changed
            if username and self.cache["users"][uid_str]["username"] != username:
                self.cache["users"][uid_str]["username"] = username
        return False

    def increment_messages(self, user_id: int, tokens: int = 0):
        """Increments message count and tokens used in RAM cache."""
        uid_str = str(user_id)
        if uid_str in self.cache["users"]:
            self.cache["users"][uid_str]["messages_sent"] += 1
            self.cache["users"][uid_str]["tokens_used"] += tokens

    def update_profile(self, user_id: int, gender: str, age: int, region: str, interest: str):
        """Updates user demographic profile in RAM cache."""
        uid_str = str(user_id)
        if uid_str in self.cache["users"]:
            self.cache["users"][uid_str]["profile"] = {
                "completed": True,
                "gender": gender,
                "age": age,
                "region": region,
                "interest": interest
            }

    def get_user(self, user_id: int) -> dict:
        """Retrieves user info from RAM cache."""
        return self.cache["users"].get(str(user_id))

    def get_all_users(self) -> dict:
        """Retrieves all users dictionary from RAM cache."""
        return self.cache.get("users", {})

    def get_footer(self) -> str:
        """Retrieves global footer text."""
        return self.cache["config"].get("global_footer", "")

    def set_footer(self, footer_text: str):
        """Sets global footer text in RAM cache."""
        self.cache["config"]["global_footer"] = footer_text

# Singleton database manager instance
db = DBManager(channel_id=config.DATABASE_CHANNEL_ID)
