import logging
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database import db
from keyboards.reply import get_main_menu
import config

logger = logging.getLogger(__name__)
router = Router()

@router.message(CommandStart())
@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    """
    Handles the /start command. Supports referral links in the format /start ref_USERID.
    Registers the user, clears FSM state, and sends welcome message.
    """
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username

    # Parse referral parameter
    referred_by = None
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referred_by = int(args[1].split("_")[1])
        except (ValueError, IndexError):
            pass

    # Register user (in MongoDB or fallback RAM Cache)
    is_new, current_credits, rewarded_id, bonus_amount = db.register_user(
        user_id=user_id,
        username=username,
        referred_by=referred_by
    )

    # Sync RAM cache to Telegram if backup mode is running
    if is_new:
        await db.save(message.bot)
        # Notify the referrer of their credit bonus
        if rewarded_id:
            try:
                await message.bot.send_message(
                    chat_id=rewarded_id,
                    text=(
                        f"🎉 **Yangi do'st taklif qilindi!**\n\n"
                        f"Siz taklif qilgan yangi a'zo botimizga qo'shildi. "
                        f"Sizga **+{bonus_amount} ta** bepul xabar limiti qo'shildi."
                    ),
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Failed to notify referrer {rewarded_id}: {e}")

    # Fetch limits settings to show remaining credits
    lim_cfg = db.get_limit_config()
    limit_enabled = lim_cfg.get("limit_enabled", True) if lim_cfg else True

    credits_info = ""
    if limit_enabled:
        credits_info = f"\n• Sizning balansingiz: *{current_credits} ta* bepul xabar."

    welcome_text = (
        f"🚀 *Assalomu alaykum, {message.from_user.first_name or 'Foydalanuvchi'}!*\n\n"
        f"Men sizning shaxsiy sun'iy ong yordamchingizman. "
        f"Menga istalgan savolingizni bering va eng to'g'ri javoblarni oling.{credits_info}\n\n"
        f"Botdan foydalanish uchun quyidagi menyuni ishlating 👇"
    )

    await message.answer(
        text=welcome_text,
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@router.message(F.text == "❌ Bekor qilish")
async def cancel_handler(message: Message, state: FSMContext):
    """
    Globally intercepts '❌ Bekor qilish' button, resets FSM state,
    and returns the user safely to the Main Tech Menu.
    """
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()

    await message.answer(
        text="❌ Harakat bekor qilindi. Bosh menyudasiz.",
        reply_markup=get_main_menu()
    )

@router.callback_query(F.data == "check_sub")
async def check_subscription_callback(callback: CallbackQuery, state: FSMContext):
    """
    Verifies forced subscription requirements.
    Unlocks bot capabilities if all subscriptions are verified.
    """
    user_id = callback.from_user.id

    # Admin bypasses FSub checking
    if user_id == config.OWNER_ID:
        await callback.answer("✅ Admin ruxsati berildi!", show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(
            "🚀 Xush kelibsiz, Admin! Botdan foydalanishingiz mumkin.",
            reply_markup=get_main_menu()
        )
        return

    # Check channels subscription
    is_subscribed = True
    for channel in config.REQUIRED_CHANNELS:
        try:
            member = await callback.bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
            if member.status not in ["member", "creator", "administrator", "owner"]:
                is_subscribed = False
                break
        except Exception:
            # Skip check on exceptions
            continue

    if is_subscribed:
        # Register user if not already done
        is_new, current_credits, rewarded_id, bonus_amount = db.register_user(
            user_id=user_id,
            username=callback.from_user.username
        )
        if is_new:
            await db.save(callback.bot)

        await callback.answer("🎉 Tabriklaymiz! Obuna tasdiqlandi.", show_alert=True)
        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer(
            "🚀 Rahmat! Barcha kanallarga a'zoligingiz tasdiqlandi. "
            "Endi botdan to'liq foydalanish imkoniyatiga egasiz.",
            reply_markup=get_main_menu()
        )
    else:
        await callback.answer("⚠️ Hali barcha kanallarga a'zo bo'lmagansiz!", show_alert=True)
