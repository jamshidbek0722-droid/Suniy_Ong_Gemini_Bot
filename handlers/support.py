import re
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states.states import SupportState
from keyboards.reply import get_cancel_menu, get_main_menu
from keyboards.inline import get_support_keyboard
from database import db
import config

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("help"))
@router.message(Command("contact"))
@router.message(F.text == "⚙️ Sozlamalar / Yordam")
async def show_help_and_contact(message: Message, state: FSMContext):
    """
    Shows help information, core commands list, and an option to contact the Admin.
    """
    await state.clear()
    
    help_text = (
        "❓ *Botdan foydalanish qo'llanmasi:*\n\n"
        "• *🤖 AI bilan Suhbat* — DeepSeek AI bilan yangi muloqot rejimini faollashtiradi.\n"
        "• *🔄 Suhbatni Yangilash* (/clear) — Rolling suhbat xotirasini butunlay tozalaydi.\n"
        "• *🔍 Savollar Tarixi* — Xotiradagi xabarlar holatini ko'rsatadi.\n"
        "• *👤 Mening Profilim* (/profile) — AI profil ma'lumotlarini to'ldirish yoki yangilash.\n"
        "• *📩 Adminga Murojaat* (/contact) — Muammolar yoki takliflar bo'yicha yozish.\n\n"
        "📖 *Tizim Buyruqlari:*\n"
        "/start - Botni ishga tushirish\n"
        "/ai - AI chat rejimiga kirish\n"
        "/clear - Tarixni tozalash\n"
        "/contact - Adminga xabar yo'llash\n"
        "/profile - Profil ma'lumotlari\n"
        "/help - Yordam qo'llanmasi\n\n"
        "Agar bot ishlashida xatolik topsangiz yoki taklifingiz bo'lsa, pastdagi tugmani bosing 👇"
    )
    
    await message.answer(
        text=help_text,
        reply_markup=get_support_keyboard(),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "contact_admin")
async def start_contact_flow(callback: CallbackQuery, state: FSMContext):
    """
    Enters SupportState.waiting_for_message.
    """
    await state.clear()
    await state.set_state(SupportState.waiting_for_message)
    
    await callback.message.answer(
        text="✍️ **Adminga yubormoqchi bo'lgan xabaringizni (savol, taklif yoki ariza) batafsil yozib yuboring:**",
        reply_markup=get_cancel_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(SupportState.waiting_for_message)
async def process_contact_message(message: Message, state: FSMContext):
    """
    Processes support query from user. Forwards it to Admin ID.
    Triggers DB save sync as feedback count shifts.
    """
    text = message.text
    if text == "❌ Bekor qilish":
        return

    user_id = message.from_user.id
    username = message.from_user.username or "mavjud emas"
    fullname = message.from_user.full_name
    
    # Notify Admin
    admin_message_text = (
        f"📩 **Yangi Murojaat!**\n\n"
        f"👤 **Foydalanuvchi:** {fullname} (@{username})\n"
        f"🆔 **Telegram ID:** `{user_id}`\n\n"
        f"💬 **Xabar:**\n{text}\n\n"
        f"✍️ _Javob yozish uchun ushbu xabarga Reply qiling._\n"
        f"---\n"
        f"Ref ID: USR_{user_id}"
    )
    
    try:
        # Send to config.ADMIN_ID
        await message.bot.send_message(
            chat_id=config.ADMIN_ID,
            text=admin_message_text,
            parse_mode="Markdown"
        )
        
        # Increment message counts in memory
        db.increment_messages(user_id, tokens=0)
        
        # Sync database with channel (Sync trigger: custom feedback / contact)
        await db.save(message.bot)
        
        await message.answer(
            text="✅ *Xabaringiz adminga yetkazildi!* Admin tez orada sizga javob qaytaradi.",
            reply_markup=get_main_menu(),
            parse_mode="Markdown"
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Failed to forward message to admin: {e}")
        await message.answer(
            text="⚠️ Xabarni yuborishda xatolik yuz berdi. Iltimos birozdan so'ng qayta urinib ko'ring.",
            reply_markup=get_main_menu()
        )
        await state.clear()

@router.message(F.chat.id == config.ADMIN_ID, F.reply_to_message)
async def handle_admin_reply(message: Message):
    """
    Listens for messages from the admin that are replies to forwarded user messages.
    Extracts user ID using regex and forwards response back to the user.
    """
    reply_text = message.reply_to_message.text or message.reply_to_message.caption
    if not reply_text:
        return
        
    # Search for user ID pattern: Ref ID: USR_(\d+)
    match = re.search(r"Ref ID: USR_(\d+)", reply_text)
    if not match:
        return
        
    target_user_id = int(match.group(1))
    admin_response = message.text
    
    user_notification = (
        f"📩 **Admindan javob keldi:**\n\n"
        f"{admin_response}"
    )
    
    try:
        await message.bot.send_message(
            chat_id=target_user_id,
            text=user_notification,
            parse_mode="Markdown"
        )
        await message.reply("✅ Javobingiz foydalanuvchiga yuborildi.")
    except Exception as e:
        logger.error(f"Failed to send admin reply to user {target_user_id}: {e}")
        await message.reply("❌ Xabarni yuborib bo'lmadi. Foydalanuvchi botni bloklagan bo'lishi mumkin.")
