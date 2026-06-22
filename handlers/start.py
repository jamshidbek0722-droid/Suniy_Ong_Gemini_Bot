from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database import db
from keyboards.reply import get_main_menu
import config

router = Router()

@router.message(CommandStart())
@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    """
    Handles the /start command. Registers the user in the RAM cache database
    if they are not already registered, clears FSM state, and sends welcome message.
    Trigger database save to channel if a new user registration occurs.
    """
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username

    # Register user in RAM cache
    is_new = db.register_user(user_id=user_id, username=username)

    # Sync RAM to Telegram channel on first-time registration
    if is_new:
        await db.save(message.bot)

    welcome_text = (
        f"🚀 *Assalomu alaykum, {message.from_user.first_name or 'Foydalanuvchi'}!*\n\n"
        f"Men *DeepSeek AI* yordamida ishlaydigan sun'iy ong yordamchisiman. "
        f"Menga xohlagan savolingizni bering va eng maqbul javoblarni oling.\n\n"
        f"Botdan to'liq foydalanish uchun quyidagi menyuni ishlating 👇"
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
    if user_id == config.ADMIN_ID:
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
            # Skip check on exceptions (e.g. channel access/ID invalid)
            continue

    if is_subscribed:
        # Register user if not already done
        is_new = db.register_user(user_id=user_id, username=callback.from_user.username)
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
