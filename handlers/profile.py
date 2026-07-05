import logging

from aiogram import Router, F

from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states.states import ProfileSurvey
from keyboards.reply import get_cancel_menu, get_main_menu
from keyboards.inline import get_gender_keyboard, get_region_keyboard, get_profile_keyboard
from database import db

logger = logging.getLogger(__name__)
router = Router()

def format_profile_text(user_id: int) -> str:
    """Formats profile statistics and survey results from cached data."""
    user = db.get_user(user_id)
    if not user:
        return "⚠️ Foydalanuvchi ma'lumotlari topilmadi."

    profile = user.get("profile", {})
    completed = profile.get("completed", False)
    
    lim_cfg = db.get_limit_config()
    limit_enabled = lim_cfg.get("limit_enabled", True) if lim_cfg else True
    credits_line = ""
    if limit_enabled:
        credits_line = f"• **Xabar limitlari balansi:** `{user.get('message_credits', 0)}` ta\n"

    stats_text = (
        f"👤 *Sizning AI Profilingiz:*\n\n"
        f"• **Telegram ID:** `{user['id']}`\n"
        f"• **Foydalanuvchi nomi:** @{user['username'] or 'mavjud emas'}\n"
        f"• **Ro'yxatdan o'tgan sana:** `{user['join_date']}`\n"
        f"• **Yuborilgan xabarlar:** `{user['messages_sent']}` ta\n"
        f"• **Sarflangan AI tokenlar:** `{user['tokens_used']}`\n"
        f"{credits_line}\n"
    )
    
    if completed:
        details = (
            f"✅ **AI So'rovnoma ma'lumotlari:**\n"
            f"• **Jinsi:** {profile.get('gender')}\n"
            f"• **Yoshi:** {profile.get('age')}\n"
            f"• **Viloyati:** {profile.get('region')}\n"
            f"• **Qiziqishi/Kasbi:** {profile.get('interest')}\n"
        )
    else:
        details = (
            f"⚠️ **AI So'rovnoma to'ldirilmagan!**\n"
            f"Sun'iy Ong sizning qiziqishlaringizga mosroq javob berishi uchun "
            f"iltimos profilingizni to'ldiring."
        )
        
    return stats_text + details

@router.message(Command("profile"))
@router.message(F.text == "👤 Mening Profilim")
async def show_profile(message: Message, state: FSMContext):
    """
    Shows user profile and stats.
    """
    await state.clear()
    user_id = message.from_user.id
    db.register_user(user_id, message.from_user.username)  # fallback check
    
    user = db.get_user(user_id)
    completed = user["profile"].get("completed", False)
    
    await message.answer(
        text=format_profile_text(user_id),
        reply_markup=get_profile_keyboard(completed),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "fill_profile")
async def start_survey(callback: CallbackQuery, state: FSMContext):
    """
    Triggers the FSM profile survey.
    Sets state to ProfileSurvey.gender.
    """
    await state.clear()
    await state.set_state(ProfileSurvey.gender)
    
    # Send a cancellation reply keyboard so the user has the '❌ Bekor qilish' button
    await callback.message.answer(
        text="🔄 AI Profilingizni shakllantirish boshlandi.",
        reply_markup=get_cancel_menu()
    )
    
    # Send gender question
    await callback.message.answer(
        text="🧑‍💼 **1. Jinsingizni tanlang:**",
        reply_markup=get_gender_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(ProfileSurvey.gender, F.data.startswith("gender_"))
async def process_gender(callback: CallbackQuery, state: FSMContext):
    """
    Saves gender and prompts for Age.
    """
    gender_value = callback.data.split("_")[1]
    await state.update_data(gender=gender_value)
    
    # Move to next state
    await state.set_state(ProfileSurvey.age)
    
    # Delete original question to clean up
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    await callback.message.answer(
        text="🔢 **2. Yoshingizni kiriting (7 dan 100 gacha raqam kiriting):**",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(ProfileSurvey.age)
async def process_age(message: Message, state: FSMContext):
    """
    Validates and saves age. Prompts for Region.
    """
    text = message.text
    if text == "❌ Bekor qilish":
        return # Handled by global cancel handler, but safety check

    try:
        age_val = int(text)
        if not (7 <= age_val <= 100):
            raise ValueError()
    except ValueError:
        await message.answer("⚠️ Iltimos, yoshingizni faqat 7 dan 100 gacha bo'lgan butun sonda kiriting:")
        return

    await state.update_data(age=age_val)
    await state.set_state(ProfileSurvey.region)
    
    await message.answer(
        text="📍 **3. Qaysi viloyat/hududdansiz? Tanlang:**",
        reply_markup=get_region_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(ProfileSurvey.region, F.data.startswith("reg_"))
async def process_region(callback: CallbackQuery, state: FSMContext):
    """
    Saves region and prompts for Interest.
    """
    region_value = callback.data.split("_")[1]
    await state.update_data(region=region_value)
    
    await state.set_state(ProfileSurvey.interest)
    
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    await callback.message.answer(
        text="💼 **4. Asosiy kasbingiz yoki qiziqishingizni yozib yuboring (masalan: Dasturchi, Shifokor, Talaba, Savdo):**",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(ProfileSurvey.interest)
async def process_interest(message: Message, state: FSMContext):
    """
    Saves interest, completes profile survey, saves data to remote channel,
    and returns user statistics screen with main menu.
    """
    text = message.text
    if text == "❌ Bekor qilish":
        return

    await state.update_data(interest=text)
    
    # Read final state data
    data = await state.get_data()
    user_id = message.from_user.id
    
    # Update profile inside RAM cache
    db.update_profile(
        user_id=user_id,
        gender=data["gender"],
        age=data["age"],
        region=data["region"],
        interest=data["interest"]
    )
    
    # Clear state context
    await state.clear()
    
    # Save/sync database to remote channel (Sync trigger: complete profile survey)
    await db.save(message.bot)
    
    await message.answer("🎉 *AI Profilingiz muvaffaqiyatli to'ldirildi!*", parse_mode="Markdown")
    
    # Display updated stats
    await message.answer(
        text=format_profile_text(user_id),
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )
