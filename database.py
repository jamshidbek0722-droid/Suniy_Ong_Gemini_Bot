import json
import logging
from datetime import datetime
import pymongo
from pymongo import MongoClient
from aiogram import Bot
from aiogram.types import BufferedInputFile, InputMediaDocument
import config

logger = logging.getLogger(__name__)

class MongoDatabase:
    """Primary MongoDB backend helper class."""
    def __init__(self, mongo_uri: str, db_channel_id: int):
        self.mongo_uri = mongo_uri
        self.db_channel_id = db_channel_id
        self.client = None
        self.db = None
        self.users = None
        self.sessions = None
        self.settings = None

    def connect(self) -> bool:
        try:
            logger.info("Connecting to MongoDB...")
            # Set short connection timeout to fail fast if local mongo is offline
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=3000)
            self.client.server_info()  # Forces connection attempt
            self.db = self.client["suniy_ong_bot"]
            self.users = self.db["users"]
            self.sessions = self.db["sessions"]
            self.settings = self.db["settings"]
            
            # Setup initial default settings document
            if not self.settings.find_one({"_id": "global_config"}):
                self.settings.insert_one({
                    "_id": "global_config",
                    "global_footer": "",
                    "free_message_limit": 20,
                    "limit_enabled": True,
                    "bonus_credits": 5
                })
            logger.info("MongoDB initialized successfully.")
            return True
        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            return False

    def register_user(self, user_id: int, username: str = None, referred_by: int = None) -> tuple[bool, int, int, int]:
        cfg = self.settings.find_one({"_id": "global_config"})
        free_limit = cfg.get("free_message_limit", 20)
        bonus_credits = cfg.get("bonus_credits", 5)

        user = self.users.find_one({"id": user_id})
        if not user:
            new_user = {
                "id": user_id,
                "username": username,
                "join_date": datetime.now().strftime("%Y-%m-%d"),
                "messages_sent": 0,
                "tokens_used": 0,
                "message_credits": free_limit,
                "referred_by": referred_by,
                "profile": {
                    "completed": False,
                    "gender": None,
                    "age": None,
                    "region": None,
                    "interest": None
                },
                "persona": "standard"
            }
            self.users.insert_one(new_user)

            # Reward referrer if exists and is not self
            rewarded_id = None
            if referred_by and referred_by != user_id:
                referrer = self.users.find_one({"id": referred_by})
                if referrer:
                    self.users.update_one(
                        {"id": referred_by},
                        {"$inc": {"message_credits": bonus_credits}}
                    )
                    rewarded_id = referred_by

            return True, free_limit, rewarded_id, bonus_credits
        else:
            if username and user.get("username") != username:
                self.users.update_one({"id": user_id}, {"$set": {"username": username}})
            return False, user.get("message_credits", 0), None, 0

    def increment_messages(self, user_id: int, tokens: int = 0):
        self.users.update_one(
            {"id": user_id},
            {"$inc": {"messages_sent": 1, "tokens_used": tokens}}
        )

    def update_profile(self, user_id: int, gender: str, age: int, region: str, interest: str):
        self.users.update_one(
            {"id": user_id},
            {
                "$set": {
                    "profile.completed": True,
                    "profile.gender": gender,
                    "profile.age": age,
                    "profile.region": region,
                    "profile.interest": interest
                }
            }
        )

    def get_user(self, user_id: int) -> dict:
        return self.users.find_one({"id": user_id})

    def get_all_users(self) -> list[dict]:
        return list(self.users.find({}))

    def get_footer(self) -> str:
        cfg = self.settings.find_one({"_id": "global_config"})
        return cfg.get("global_footer", "") if cfg else ""

    def set_footer(self, footer_text: str):
        self.settings.update_one(
            {"_id": "global_config"},
            {"$set": {"global_footer": footer_text}}
        )

    def get_user_persona(self, user_id: int) -> str:
        user = self.get_user(user_id)
        return user.get("persona", "standard") if user else "standard"

    def set_user_persona(self, user_id: int, persona: str) -> bool:
        res = self.users.update_one({"id": user_id}, {"$set": {"persona": persona}})
        return res.modified_count > 0

    def get_chat_history(self, user_id: int) -> list[dict]:
        session = self.sessions.find_one({"_id": str(user_id)})
        return session.get("messages", []) if session else []

    def add_chat_message(self, user_id: int, role: str, content: str):
        session = self.sessions.find_one({"_id": str(user_id)})
        messages = session.get("messages", []) if session else []
        
        messages.append({"role": role, "content": content})
        if len(messages) > 15:
            messages = messages[-15:]

        self.sessions.update_one(
            {"_id": str(user_id)},
            {"$set": {"messages": messages, "updated_at": datetime.now()}},
            upsert=True
        )

    def clear_chat_history(self, user_id: int):
        self.sessions.delete_one({"_id": str(user_id)})

    def deduct_credit(self, user_id: int) -> int:
        cfg = self.settings.find_one({"_id": "global_config"})
        if not cfg.get("limit_enabled", True):
            return -1

        user = self.get_user(user_id)
        if user:
            new_credits = max(0, user.get("message_credits", 0) - 1)
            self.users.update_one({"id": user_id}, {"$set": {"message_credits": new_credits}})
            return new_credits
        return 0

    def get_limit_config(self) -> dict:
        return self.settings.find_one({"_id": "global_config"})

    def update_limit_config(self, enabled: bool, limit: int):
        self.settings.update_one(
            {"_id": "global_config"},
            {"$set": {"limit_enabled": enabled, "free_message_limit": limit}}
        )

    def get_analytics(self) -> dict:
        total_users = self.users.count_documents({})
        completed_profiles = self.users.count_documents({"profile.completed": True})

        # Gender Aggregation
        gender_agg = list(self.users.aggregate([
            {"$match": {"profile.completed": True}},
            {"$group": {"_id": "$profile.gender", "count": {"$sum": 1}}}
        ]))
        gender_counts = {"Erkak": 0, "Ayol": 0}
        for item in gender_agg:
            g = item["_id"]
            if g in gender_counts:
                gender_counts[g] = item["count"]

        # Average Age Aggregation
        avg_age_agg = list(self.users.aggregate([
            {"$match": {"profile.completed": True}},
            {"$group": {"_id": None, "avg_age": {"$avg": "$profile.age"}}}
        ]))
        overall_avg_age = avg_age_agg[0]["avg_age"] if avg_age_agg else 0

        # Region aggregation with Region average age
        region_agg = list(self.users.aggregate([
            {"$match": {"profile.completed": True}},
            {"$group": {
                "_id": "$profile.region",
                "count": {"$sum": 1},
                "avg_age": {"$avg": "$profile.age"}
            }},
            {"$sort": {"count": -1}}
        ]))

        # Age group aggregation buckets
        age_agg = list(self.users.aggregate([
            {"$match": {"profile.completed": True}},
            {"$bucket": {
                "groupBy": "$profile.age",
                "boundaries": [7, 18, 26, 36, 51, 101],
                "default": "Other",
                "output": {"count": {"$sum": 1}}
            }}
        ]))
        age_brackets = {
            "7-17 yosh": 0,
            "18-25 yosh": 0,
            "26-35 yosh": 0,
            "36-50 yosh": 0,
            "50+ yosh": 0
        }
        for item in age_agg:
            b = item["_id"]
            cnt = item["count"]
            if b == 7:
                age_brackets["7-17 yosh"] = cnt
            elif b == 18:
                age_brackets["18-25 yosh"] = cnt
            elif b == 26:
                age_brackets["26-35 yosh"] = cnt
            elif b == 36:
                age_brackets["36-50 yosh"] = cnt
            elif b == 51:
                age_brackets["50+ yosh"] = cnt

        return {
            "total_users": total_users,
            "completed_profiles": completed_profiles,
            "gender_counts": gender_counts,
            "overall_avg_age": overall_avg_age,
            "region_breakdown": region_agg,
            "age_brackets": age_brackets
        }


class InMemoryDatabase:
    """Fallback Local RAM + Telegram File sync backend."""
    def __init__(self, db_channel_id: int):
        self.db_channel_id = db_channel_id
        self.pinned_msg_id = None
        self.cache = {
            "users": {},
            "config": {
                "global_footer": "",
                "free_message_limit": 20,
                "limit_enabled": True,
                "bonus_credits": 5
            }
        }
        self.history_cache = {}

    async def load_from_telegram(self, bot: Bot):
        try:
            logger.info("Initializing RAM Cache from Telegram channel database...")
            chat = await bot.get_chat(chat_id=self.db_channel_id)
            pinned_msg = chat.pinned_message
            
            if pinned_msg and pinned_msg.document and pinned_msg.document.file_name == "index.json":
                file_id = pinned_msg.document.file_id
                file = await bot.get_file(file_id)
                result = await bot.download(file)
                file_bytes = result.read()
                
                self.cache = json.loads(file_bytes.decode('utf-8'))
                self.pinned_msg_id = pinned_msg.message_id
                logger.info(f"RAM DB sync complete. Cached users: {len(self.cache.get('users', {}))}")
            else:
                await self._create_new_file_db(bot)
        except Exception as e:
            logger.error(f"Fallback RAM Cache initialization error: {e}")
            await self._create_new_file_db(bot)

    async def _create_new_file_db(self, bot: Bot):
        try:
            data_bytes = json.dumps(self.cache, indent=2).encode('utf-8')
            sent_msg = await bot.send_document(
                chat_id=self.db_channel_id,
                document=BufferedInputFile(data_bytes, filename="index.json"),
                caption="Sun'iy Ong Gemini Bot Pinned Database Fallback"
            )
            await bot.pin_chat_message(chat_id=self.db_channel_id, message_id=sent_msg.message_id)
            self.pinned_msg_id = sent_msg.message_id
        except Exception as e:
            logger.critical(f"Failed to pin database fallback file on Telegram: {e}")
            self.pinned_msg_id = 999999999

    async def sync_to_telegram(self, bot: Bot):
        if not self.pinned_msg_id or self.pinned_msg_id == 999999999:
            return False
        try:
            data_bytes = json.dumps(self.cache, indent=2).encode('utf-8')
            await bot.edit_message_media(
                chat_id=self.db_channel_id,
                message_id=self.pinned_msg_id,
                media=InputMediaDocument(
                    media=BufferedInputFile(data_bytes, filename="index.json"),
                    caption=f"Sun'iy Ong Pinned Database (Synced: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
                )
            )
            return True
        except Exception as e:
            logger.error(f"Failed to sync backup database to Telegram: {e}")
            return False

    def register_user(self, user_id: int, username: str = None, referred_by: int = None) -> tuple[bool, int, int, int]:
        uid_str = str(user_id)
        cfg = self.cache["config"]
        free_limit = cfg.get("free_message_limit", 20)
        bonus_credits = cfg.get("bonus_credits", 5)

        if uid_str not in self.cache["users"]:
            self.cache["users"][uid_str] = {
                "id": user_id,
                "username": username,
                "join_date": datetime.now().strftime("%Y-%m-%d"),
                "messages_sent": 0,
                "tokens_used": 0,
                "message_credits": free_limit,
                "referred_by": referred_by,
                "profile": {
                    "completed": False,
                    "gender": None,
                    "age": None,
                    "region": None,
                    "interest": None
                },
                "persona": "standard"
            }

            rewarded_id = None
            if referred_by and referred_by != user_id:
                ref_str = str(referred_by)
                if ref_str in self.cache["users"]:
                    self.cache["users"][ref_str]["message_credits"] = self.cache["users"][ref_str].get("message_credits", 0) + bonus_credits
                    rewarded_id = referred_by

            return True, free_limit, rewarded_id, bonus_credits
        else:
            if username and self.cache["users"][uid_str]["username"] != username:
                self.cache["users"][uid_str]["username"] = username
            return False, self.cache["users"][uid_str].get("message_credits", 0), None, 0

    def increment_messages(self, user_id: int, tokens: int = 0):
        uid_str = str(user_id)
        if uid_str in self.cache["users"]:
            self.cache["users"][uid_str]["messages_sent"] += 1
            self.cache["users"][uid_str]["tokens_used"] += tokens

    def update_profile(self, user_id: int, gender: str, age: int, region: str, interest: str):
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
        return self.cache["users"].get(str(user_id))

    def get_all_users(self) -> list[dict]:
        return list(self.cache["users"].values())

    def get_footer(self) -> str:
        return self.cache["config"].get("global_footer", "")

    def set_footer(self, footer_text: str):
        self.cache["config"]["global_footer"] = footer_text

    def get_user_persona(self, user_id: int) -> str:
        user = self.get_user(user_id)
        return user.get("persona", "standard") if user else "standard"

    def set_user_persona(self, user_id: int, persona: str) -> bool:
        uid_str = str(user_id)
        if uid_str in self.cache["users"]:
            self.cache["users"][uid_str]["persona"] = persona
            return True
        return False

    def get_chat_history(self, user_id: int) -> list[dict]:
        return self.history_cache.get(user_id, [])

    def add_chat_message(self, user_id: int, role: str, content: str):
        if user_id not in self.history_cache:
            self.history_cache[user_id] = []
        self.history_cache[user_id].append({"role": role, "content": content})
        if len(self.history_cache[user_id]) > 15:
            self.history_cache[user_id] = self.history_cache[user_id][-15:]

    def clear_chat_history(self, user_id: int):
        if user_id in self.history_cache:
            del self.history_cache[user_id]

    def deduct_credit(self, user_id: int) -> int:
        cfg = self.cache["config"]
        if not cfg.get("limit_enabled", True):
            return -1

        uid_str = str(user_id)
        if uid_str in self.cache["users"]:
            new_credits = max(0, self.cache["users"][uid_str].get("message_credits", 0) - 1)
            self.cache["users"][uid_str]["message_credits"] = new_credits
            return new_credits
        return 0

    def get_limit_config(self) -> dict:
        cfg = self.cache["config"]
        return {
            "limit_enabled": cfg.get("limit_enabled", True),
            "free_message_limit": cfg.get("free_message_limit", 20),
            "bonus_credits": cfg.get("bonus_credits", 5)
        }

    def update_limit_config(self, enabled: bool, limit: int):
        self.cache["config"]["limit_enabled"] = enabled
        self.cache["config"]["free_message_limit"] = limit

    def get_analytics(self) -> dict:
        users = self.cache["users"]
        total_users = len(users)
        completed_profiles = 0
        gender_counts = {"Erkak": 0, "Ayol": 0}
        region_ages = {}
        ages = []
        age_brackets = {
            "7-17 yosh": 0,
            "18-25 yosh": 0,
            "26-35 yosh": 0,
            "36-50 yosh": 0,
            "50+ yosh": 0
        }

        for u in users.values():
            prof = u.get("profile", {})
            if prof.get("completed"):
                completed_profiles += 1
                g = prof.get("gender")
                if g in gender_counts:
                    gender_counts[g] += 1

                age = int(prof.get("age", 0))
                ages.append(age)

                if 7 <= age <= 17:
                    age_brackets["7-17 yosh"] += 1
                elif 18 <= age <= 25:
                    age_brackets["18-25 yosh"] += 1
                elif 26 <= age <= 35:
                    age_brackets["26-35 yosh"] += 1
                elif 36 <= age <= 50:
                    age_brackets["36-50 yosh"] += 1
                elif age > 50:
                    age_brackets["50+ yosh"] += 1

                r = prof.get("region")
                if r:
                    if r not in region_ages:
                        region_ages[r] = []
                    region_ages[r].append(age)

        overall_avg_age = sum(ages) / len(ages) if ages else 0

        region_breakdown = []
        for r, r_ages in region_ages.items():
            region_breakdown.append({
                "_id": r,
                "count": len(r_ages),
                "avg_age": sum(r_ages) / len(r_ages)
            })
        region_breakdown.sort(key=lambda x: x["count"], reverse=True)

        return {
            "total_users": total_users,
            "completed_profiles": completed_profiles,
            "gender_counts": gender_counts,
            "overall_avg_age": overall_avg_age,
            "region_breakdown": region_breakdown,
            "age_brackets": age_brackets
        }


class DBManager:
    """Unified Database Router that switches dynamically between MongoDB and Backup RAM Cache."""
    def __init__(self):
        self.mongo = MongoDatabase(mongo_uri=config.MONGO_URI, db_channel_id=config.DB_CHANNEL_ID)
        self.ram = InMemoryDatabase(db_channel_id=config.DB_CHANNEL_ID)
        self.is_mongo = False

    async def initialize(self, bot: Bot):
        # Attempt MongoDB connection
        self.is_mongo = self.mongo.connect()
        if not self.is_mongo:
            # Fallback to local file RAM sync on Telegram Channel
            await self.ram.load_from_telegram(bot)

    async def save(self, bot: Bot) -> bool:
        """Required for syncing InMemoryDatabase back to Channel."""
        if not self.is_mongo:
            return await self.ram.sync_to_telegram(bot)
        return True

    def register_user(self, user_id: int, username: str = None, referred_by: int = None) -> tuple[bool, int, int, int]:
        if self.is_mongo:
            return self.mongo.register_user(user_id, username, referred_by)
        return self.ram.register_user(user_id, username, referred_by)

    def increment_messages(self, user_id: int, tokens: int = 0):
        if self.is_mongo:
            self.mongo.increment_messages(user_id, tokens)
        else:
            self.ram.increment_messages(user_id, tokens)

    def update_profile(self, user_id: int, gender: str, age: int, region: str, interest: str):
        if self.is_mongo:
            self.mongo.update_profile(user_id, gender, age, region, interest)
        else:
            self.ram.update_profile(user_id, gender, age, region, interest)

    def get_user(self, user_id: int) -> dict:
        if self.is_mongo:
            return self.mongo.get_user(user_id)
        return self.ram.get_user(user_id)

    def get_all_users(self) -> list[dict]:
        if self.is_mongo:
            return self.mongo.get_all_users()
        return self.ram.get_all_users()

    def get_footer(self) -> str:
        if self.is_mongo:
            return self.mongo.get_footer()
        return self.ram.get_footer()

    def set_footer(self, footer_text: str):
        if self.is_mongo:
            self.mongo.set_footer(footer_text)
        else:
            self.ram.set_footer(footer_text)

    def get_user_persona(self, user_id: int) -> str:
        if self.is_mongo:
            return self.mongo.get_user_persona(user_id)
        return self.ram.get_user_persona(user_id)

    def set_user_persona(self, user_id: int, persona: str) -> bool:
        if self.is_mongo:
            return self.mongo.set_user_persona(user_id, persona)
        return self.ram.set_user_persona(user_id, persona)

    def get_chat_history(self, user_id: int) -> list[dict]:
        if self.is_mongo:
            return self.mongo.get_chat_history(user_id)
        return self.ram.get_chat_history(user_id)

    def add_chat_message(self, user_id: int, role: str, content: str):
        if self.is_mongo:
            self.mongo.add_chat_message(user_id, role, content)
        else:
            self.ram.add_chat_message(user_id, role, content)

    def clear_chat_history(self, user_id: int):
        if self.is_mongo:
            self.mongo.clear_chat_history(user_id)
        else:
            self.ram.clear_chat_history(user_id)

    def deduct_credit(self, user_id: int) -> int:
        if self.is_mongo:
            return self.mongo.deduct_credit(user_id)
        return self.ram.deduct_credit(user_id)

    def get_limit_config(self) -> dict:
        if self.is_mongo:
            return self.mongo.get_limit_config()
        return self.ram.get_limit_config()

    def update_limit_config(self, enabled: bool, limit: int):
        if self.is_mongo:
            self.mongo.update_limit_config(enabled, limit)
        else:
            self.ram.update_limit_config(enabled, limit)

    def get_analytics(self) -> dict:
        if self.is_mongo:
            return self.mongo.get_analytics()
        return self.ram.get_analytics()

db = DBManager()
