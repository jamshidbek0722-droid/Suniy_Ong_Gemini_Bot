import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states.states import AdminState
from keyboards.reply import get_admin_menu, get_main_menu
from database import db
import config

logger = logging.getLogger(__name__)
router = Router()

# Inline check to secure admin routes
is_admin = F.from_user.id == config.ADMIN_ID

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
    and prints a formatted breakdown report.
    """
    users = db.get_all_users()
    total_users = len(users)
    
    if total_users == 0:
        await message.answer("⚠️ Botda hali foydalanuvchilar ro'yxatga olinmagan.")
        return

    completed_profiles = 0
    gender_counts = {"Erkak": 0, "Ayol": 0}
    region_counts = {}
    
    # Age brackets
    age_brackets = {
        "7-17 yosh": 0,
        "18-25 yosh": 0,
        "26-35 yosh": 0,
        "36-50 yosh": 0,
        "50+ yosh": 0
    }

    for uid, user_data in users.items():
        profile = user_data.get("profile", {})
        if profile.get("completed", False):
            completed_profiles += 1
            
            # Gender counts
            gender = profile.get("gender")
            if gender in gender_counts:
                gender_counts[gender] += 1
                
            # Region counts
            reg = profile.get("region")
            if reg:
                region_counts[reg] = region_counts.get(reg, 0) + 1
                
            # Age grouping
            try:
                age = int(profile.get("age", 0))
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
            except (ValueError, TypeError):
                continue

    completed_pct = (completed_profiles / total_users) * 100
    
    # Gender details
    erkak = gender_counts["Erkak"]
    ayol = gender_counts["Ayol"]
    known_gender_total = erkak + ayol
    erkak_pct = (erkak / known_gender_total * 100) if known_gender_total > 0 else 0
    ayol_pct = (ayol / known_gender_total * 100) if known_gender_total > 0 else 0
    unknown_gender = total_users - completed_profiles

    # Region details format
    region_lines = []
    if region_counts:
        # Sort regions by count descending
        sorted_regions = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)
        for r_name, r_cnt in sorted_regions:
            r_pct = (r_cnt / completed_profiles) * 100
            region_lines.append(f" • {r_name}: *{r_cnt} ta* ({r_pct:.1f}%)")
    else:
        region_lines.append(" • Ma'lumot mavjud emas")
        
    regions_breakdown = "\n".join(region_lines)

    # Format the report
    report_text = (
        f"📊 **DEEP BOT ANALITIKASI HISOBOТI**\n\n"
        f"👥 **Jami a'zolar:** *{total_users} ta*\n"
        f"✅ **Profil to'ldirganlar:** *{completed_profiles} ta* ({completed_pct:.1f}%)\n\n"
        f"👤 **Jins nisbati (Profil to'ldirganlar):**\n"
        f" • Erkaklar: *{erkak} ta* ({erkak_pct:.1f}%)\n"
        f" • Ayollar: *{ayol} ta* ({ayol_pct:.1f}%)\n"
        f" • Hali profil to'ldirmagan: *{unknown_gender} ta*\n\n"
        f"📍 **Hududlar bo'yicha taqsimot:**\n"
        f"{regions_breakdown}\n\n"
        f"🔢 **Yosh guruhlari taqsimoti:**\n"
        f" • 7-17 yosh: *{age_brackets['7-17 yosh']} ta*\n"
        f" • 18-25 yosh: *{age_brackets['18-25 yosh']} ta*\n"
        f" • 26-35 yosh: *{age_brackets['26-35 yosh']} ta*\n"
        f" • 36-50 yosh: *{age_brackets['36-50 yosh']} ta*\n"
        f" • 50+ yosh: *{age_brackets['50+ yosh']} ta*"
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
    Saves the new footer in RAM config cache, then syncs/saves database to channel.
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
    
    # Sync database with channel (Sync trigger: admin configuration shifts)
    await db.save(message.bot)
    
    await message.answer(
        text=success_msg,
        reply_markup=get_admin_menu(),
        parse_mode="Markdown"
    )
