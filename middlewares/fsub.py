from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
import config
from keyboards.inline import get_fsub_keyboard

class ForcedSubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        user_id = None
        is_bypass = False

        if isinstance(event, Message):
            if event.from_user:
                user_id = event.from_user.id
            # Allow /start command to pass so new users can initiate the bot
            if event.text and event.text.startswith("/start"):
                is_bypass = True

        elif isinstance(event, CallbackQuery):
            if event.from_user:
                user_id = event.from_user.id
            # Allow the check_sub callback query to pass so users can verify subscription
            if event.data == "check_sub":
                is_bypass = True

        # If we cannot resolve user_id, let it pass
        if not user_id:
            return await handler(event, data)

        # Bypass checks for the bot Admin
        if user_id == config.ADMIN_ID:
            return await handler(event, data)

        if is_bypass:
            return await handler(event, data)

        # Check membership status in each required channel
        for channel in config.REQUIRED_CHANNELS:
            try:
                member = await event.bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
                if member.status not in ["member", "creator", "administrator", "owner"]:
                    text = (
                        "⚠️ **Botdan foydalanish uchun quyidagi rasmiy kanallarga a'zo bo'lishingiz lozim!**\n\n"
                        "Obuna bo'lganingizdan so'ng **[✅ Obunani Tekshirish]** tugmasini bosing."
                    )
                    markup = get_fsub_keyboard()
                    
                    if isinstance(event, Message):
                        await event.answer(text, reply_markup=markup, parse_mode="Markdown")
                    elif isinstance(event, CallbackQuery):
                        await event.answer("⚠️ Botdan foydalanish uchun avval kanallarga a'zo bo'ling!", show_alert=True)
                        await event.message.answer(text, reply_markup=markup, parse_mode="Markdown")
                    return
            except Exception:
                # If bot lacks access to check status (e.g. channel ID changes), skip that channel check
                continue

        # If subscribed, pass to handler
        return await handler(event, data)
