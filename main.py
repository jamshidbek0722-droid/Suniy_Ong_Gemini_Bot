import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from database import db
import config

# Import handlers
from handlers import start, ai_chat, profile, support, admin

# Import middleware
from middlewares.fsub import ForcedSubscriptionMiddleware

# Configure logger
logger = logging.getLogger(__name__)

async def main():
    # Setup logging format
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger.info("Initializing Telegram AI Bot dispatcher...")
    
    # Initialize bot and dispatcher
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    # Register Forced Subscription middlewares
    dp.message.middleware(ForcedSubscriptionMiddleware())
    dp.callback_query.middleware(ForcedSubscriptionMiddleware())

    # Include routers in correct order (Admin handlers first, then conversational flows)
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(ai_chat.router)
    dp.include_router(profile.router)
    dp.include_router(support.router)

    # Register startup hooks
    @dp.startup()
    async def on_startup(bot: Bot):
        # 1. Pull the pinned database document from channel
        try:
            await db.initialize(bot)
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}. Bot will run with in-memory database fallback.")
        
        # 2. Register the 6 core system commands natively in the client menu
        try:
            commands = [
                BotCommand(command="start", description="🚀 Botni ishga tushirish va AI bilan tanishuv"),
                BotCommand(command="ai", description="🤖 Yangi suhbat oynasini ochish"),
                BotCommand(command="clear", description="🔄 Chat tarixini (kontekstni) tozalash"),
                BotCommand(command="contact", description="📩 Adminga xabar/taklif yo'llash"),
                BotCommand(command="profile", description="👤 Shaxsiy AI Profilingiz"),
                BotCommand(command="help", description="❓ Botdan foydalanish qo'llanmasi")
            ]
            await bot.set_my_commands(commands)
            logger.info("Startup sequence complete. Commands registered and DB loaded.")
        except Exception as e:
            logger.error(f"Failed to set bot commands: {e}. Bot will continue starting up.")

    # Begin polling
    logger.info("Starting bot long polling...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.critical(f"Critical error in bot polling loop: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot execution terminated.")
