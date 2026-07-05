import logging
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states.states import AdminState
from keyboards.reply import get_admin_menu, get_main_menu
from keyboards.inline import get_limit_settings_keyboard
from database import db
import config

logger = logging.getLogger(__name__)
router = Router()

# Secure admin routes
is_admin = F.from_user.id == config.OWNER_ID

@router.message(Command("admin"), is_admin)
async def admin_menu_handler(message: Message, state: FSMContext):
    """
    Shows the administrative dashboard menu.
    """
    await state.clear()
    await message.answer(
        text="📊 *Admin paneliga xush kelibsiz!* Kerakli operatsiyani tanlang:",
        reply_markup=get_admin_menu(),
        parse_mode="Markdown"
    )

@router.message(F.text == "📊 Analitika Panel", is_admin)
@router.message(Command("analytics"), is_admin)
async def show_analytics(message: Message):
    """
    Calculates detailed segmentation statistics of the users
    and prints a formatted breakdown report including average ages.
    """
    analytics = db.get_analytics()
    total_users = analytics.get("total_users", 0)
    
    if total_users == 0:
        await message.answer("⚠️ Botda hali foydalanuvchilar ro'yxatga olinmagan.")
        return

    completed_profiles = analytics.get("completed_profiles", 0)
    completed_pct = (completed_profiles / total_users) * 100 if total_users > 0 else 0
    
    # Gender details
    gender_counts = analytics.get("gender_counts", {"Erkak": 0, "Ayol": 0})
    erkak = gender_counts.get("Erkak", 0)
    ayol = gender_counts.get("Ayol", 0)
    known_gender_total = erkak + ayol
    erkak_pct = (erkak / known_gender_total * 100) if known_gender_total > 0 else 0
    ayol_pct = (ayol / known_gender_total * 100) if known_gender_total > 0 else 0
    unknown_gender = total_users - completed_profiles

    # Region details format with average age per region
    region_lines = []
    region_breakdown = analytics.get("region_breakdown", [])
    if region_breakdown:
        for r_data in region_breakdown:
            r_name = r_data["_id"]
            r_cnt = r_data["count"]
            r_avg = r_data.get("avg_age", 0)
            r_pct = (r_cnt / completed_profiles) * 100 if completed_profiles > 0 else 0
            region_lines.append(f" • {r_name}: *{r_cnt} ta* ({r_pct:.1f}%), O'rtacha yosh: *{r_avg:.1f} yosh*")
    else:
        region_lines.append(" • Ma'lumot mavjud emas")
        
    regions_breakdown = "\n".join(region_lines)
    overall_avg = analytics.get("overall_avg_age", 0)
    age_brackets = analytics.get("age_brackets", {})

    report_text = (
        f"📊 **BOT ANALITIKASI HISOBOТI**\n\n"
        f"👥 **Jami a'zolar:** *{total_users} ta*\n"
        f"✅ **Profil to'ldirganlar:** *{completed_profiles} ta* ({completed_pct:.1f}%)\n"
        f"🧠 **Umumiy o'rtacha yosh:** *{overall_avg:.1f} yosh*\n\n"
        f"👤 **Jins nisbati (Profil to'ldirganlar):**\n"
        f" • Erkaklar: *{erkak} ta* ({erkak_pct:.1f}%)\n"
        f" • Ayollar: *{ayol} ta* ({ayol_pct:.1f}%)\n"
        f" • Hali profil to'ldirmagan: *{unknown_gender} ta*\n\n"
        f"📍 **Hududlar bo'yicha taqsimot va o'rtacha yosh:**\n"
        f"{regions_breakdown}\n\n"
        f"🔢 **Yosh guruhlari taqsimoti:**\n"
        f" • 7-17 yosh: *{age_brackets.get('7-17 yosh', 0)} ta*\n"
        f" • 18-25 yosh: *{age_brackets.get('18-25 yosh', 0)} ta*\n"
        f" • 26-35 yosh: *{age_brackets.get('26-35 yosh', 0)} ta*\n"
        f" • 36-50 yosh: *{age_brackets.get('36-50 yosh', 0)} ta*\n"
        f" • 50+ yosh: *{age_brackets.get('50+ yosh', 0)} ta*"
    )

    await message.answer(text=report_text, parse_mode="Markdown")

@router.message(F.text == "📢 Footer O'zgartirish", is_admin)
@router.message(Command("setfooter"), is_admin)
async def start_footer_change(message: Message, state: FSMContext):
    """
    Prompts admin to enter the new advertising footer.
    """
    await state.clear()
    await state.set_state(AdminState.waiting_for_footer)
    
    current_footer = db.get_footer() or "Hozircha reklama footeri o'rnatilmagan."
    
    await message.answer(
        text=(
            f"📢 **Global Reklama Footeri**\n\n"
            f"Hozirgi holat:\n`{current_footer}`\n\n"
            f"AI javoblari ostiga qo'shiladigan yangi matnni yozib yuboring. "
            f"Footer-ni butunlay o'chirish uchun `none` yoki `o'chirish` deb yozing:"
        ),
        reply_markup=get_admin_menu(),
        parse_mode="Markdown"
    )

@router.message(AdminState.waiting_for_footer, is_admin)
async def process_footer_change(message: Message, state: FSMContext):
    """
    Saves the new footer in database config cache.
    """
    text = message.text
    if text == "❌ Bekor qilish":
        return

    if text.lower() in ["none", "o'chirish"]:
        db.set_footer("")
        success_msg = "✅ Reklama footeri muvaffaqiyatli o'chirildi!"
    else:
        db.set_footer(text)
        success_msg = f"✅ Reklama footeri muvaffaqiyatli saqlandi!\n\nYangilangan footer:\n`{text}`"
        
    await state.clear()
    await db.save(message.bot)
    
    await message.answer(
        text=success_msg,
        reply_markup=get_admin_menu(),
        parse_mode="Markdown"
    )

@router.message(F.text == "⚙️ Limitlarni Sozlash", is_admin)
@router.message(Command("limit"), is_admin)
async def show_limit_settings(message: Message, state: FSMContext):
    """
    Shows control keyboard for setting/disabling global freemium credits.
    """
    await state.clear()
    cfg = db.get_limit_config()
    enabled = cfg.get("limit_enabled", True) if cfg else True
    limit = cfg.get("free_message_limit", 20) if cfg else 20

    status_text = "FAOL ✅" if enabled else "O'CHIRILGAN ❌"
    text = (
        "⚙️ **Global Limitlarni Sozlash**\n\n"
        f"• Limit rejimi: **{status_text}**\n"
        f"• Bepul xabarlar limiti: **{limit} ta**\n\n"
        "Sozlash uchun quyidagi tugmalardan foydalaning 👇"
    )
    await message.answer(
        text=text,
        reply_markup=get_limit_settings_keyboard(enabled),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_toggle_limit", is_admin)
async def toggle_limit_mode(callback: CallbackQuery):
    cfg = db.get_limit_config()
    enabled = cfg.get("limit_enabled", True) if cfg else True
    limit = cfg.get("free_message_limit", 20) if cfg else 20

    new_mode = not enabled
    db.update_limit_config(new_mode, limit)
    await db.save(callback.message.bot)

    status_text = "FAOL ✅" if new_mode else "O'CHIRILGAN ❌"
    await callback.message.edit_text(
        text=(
            "⚙️ **Global Limitlarni Sozlash**\n\n"
            f"• Limit rejimi: **{status_text}**\n"
            f"• Bepul xabarlar limiti: **{limit} ta**\n\n"
            "Sozlash uchun quyidagi tugmalardan foydalaning 👇"
        ),
        reply_markup=get_limit_settings_keyboard(new_mode),
        parse_mode="Markdown"
    )
    await callback.answer("Limit rejimi o'zgartirildi!")

@router.callback_query(F.data == "admin_change_limit", is_admin)
async def prompt_limit_value(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_for_limit_value)
    await callback.message.answer(
        text="🔢 **Yangi bepul xabarlar soni limitini yuboring (butun son, masalan, 25):**",
        reply_markup=get_admin_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AdminState.waiting_for_limit_value, is_admin)
async def process_new_limit_value(message: Message, state: FSMContext):
    text = message.text
    if text == "❌ Bekor qilish":
        return

    try:
        new_val = int(text)
        if new_val < 0:
            raise ValueError()
    except ValueError:
        await message.answer("⚠️ Iltimos, limit qiymatini faqat musbat butun sonda yuboring:")
        return

    cfg = db.get_limit_config()
    enabled = cfg.get("limit_enabled", True) if cfg else True

    db.update_limit_config(enabled, new_val)
    await db.save(message.bot)
    await state.clear()

    await message.answer(
        text=f"✅ **Yangi bepul xabarlar limiti muvaffaqiyatli o'rnatildi:** **{new_val} ta**",
        reply_markup=get_admin_menu(),
        parse_mode="Markdown"
    )

@router.message(F.text == "📢 Reklama Jo'natish", is_admin)
@router.message(Command("broadcast"), is_admin)
async def start_broadcast(message: Message, state: FSMContext):
    """
    Prompts admin to send the message to be broadcasted to all users.
    """
    await state.clear()
    await state.set_state(AdminState.waiting_for_broadcast)
    await message.answer(
        text=(
            "📢 **Barcha a'zolarga reklama yuborish bo'limi**\n\n"
            "Yubormoqchi bo'lgan xabaringizni yuboring (matn, rasm, video, havola hammasini o'z holicha yetkazaman):"
        ),
        reply_markup=get_admin_menu(),
        parse_mode="Markdown"
    )

@router.message(AdminState.waiting_for_broadcast, is_admin)
async def process_broadcast(message: Message, state: FSMContext):
    """
    Broadcasts the message losslessly using message.copy_to().
    """
    text = message.text
    if text == "❌ Bekor qilish":
        return

    users = db.get_all_users()
    
    await message.answer("⏳ Reklama yuborish boshlandi. Iltimos kuting...")
    
    success = 0
    failed = 0

    for user in users:
        uid = user.get("id")
        if not uid:
            continue
        try:
            # Lossless delivery (retains styling, links, photos, layout)
            await message.copy_to(chat_id=uid)
            success += 1
            # Avoid hitting Telegram flooding limit
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await state.clear()
    
    report = (
        "📢 **Reklama jo'natish yakunlandi:**\n\n"
        f"• Muvaffaqiyatli yuborildi: *{success} ta*\n"
        f"• Yuborib bo'lmadi (botni tark etganlar): *{failed} ta*"
    )
    await message.answer(
        text=report,
        reply_markup=get_admin_menu(),
        parse_mode="Markdown"
    )
