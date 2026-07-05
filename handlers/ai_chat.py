import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states.states import AIChatState
from keyboards.reply import get_cancel_menu, get_main_menu
from external_api import get_ai_response
from database import db

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("ai"))
@router.message(F.text == "🤖 AI bilan Suhbat")
async def enter_ai_chat(message: Message, state: FSMContext):
    """
    Triggers FSM context to enter AIChatState.chatting.
    Informs user they are chatting with their personal AI.
    """
    await state.set_state(AIChatState.chatting)
    await message.answer(
        text=(
            "🤖 *Sun'iy ong yordamchisi bilan suhbat boshlandi!*\n\n"
            "Menga xohlagan savolingizni yuborishingiz mumkin. "
            "Suhbatdan chiqish uchun quyidagi *❌ Bekor qilish* tugmasini bosing."
        ),
        reply_markup=get_cancel_menu(),
        parse_mode="Markdown"
    )

@router.message(Command("clear"))
@router.message(Command("reset"))
@router.message(F.text == "🔄 Suhbatni Yangilash")
async def clear_chat_history(message: Message, state: FSMContext):
    """
    Clears user's rolling chat history context.
    """
    user_id = message.from_user.id
    db.clear_chat_history(user_id)
    
    current_state = await state.get_state()
    
    # Send response and keep them in appropriate keyboard layout
    if current_state == AIChatState.chatting:
        await message.answer(
            text="🔄 *Suhbat tarixi muvaffaqiyatli tozalandi!* Yangi savolingizni yo'llashingiz mumkin.",
            reply_markup=get_cancel_menu(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            text="🔄 *Suhbat tarixi muvaffaqiyatli tozalandi!*",
            reply_markup=get_main_menu(),
            parse_mode="Markdown"
        )

@router.message(F.text == "🔍 Savollar Tarixi")
async def show_chat_history_status(message: Message):
    """
    Shows metrics about the current rolling history in database.
    """
    user_id = message.from_user.id
    history = db.get_chat_history(user_id)
    
    turns_count = len(history) // 2
    messages_count = len(history)
    
    await message.answer(
        text=(
            f"🔍 *Savollar Tarixi:*\n\n"
            f"• Hozirgi suhbatda: *{turns_count} ta muloqot* (jami {messages_count} ta xabar)\n"
            f"• Maksimal xotira: *15 ta xabar* (Undan eskilari o'chiriladi)\n\n"
            f"Tarixni tozalash uchun *🔄 Suhbatni Yangilash* tugmasini bosing."
        ),
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@router.message(AIChatState.chatting)
async def ai_chat_handler(message: Message, state: FSMContext):
    """
    Processes messages when user is in active chatting state.
    Validates freemium limits, decrements credits, displays typing indicator,
    sends query to Groq, and appends footers.
    """
    # Prevent handling button click texts as prompts
    if message.text in ["❌ Bekor qilish", "🔄 Suhbatni Yangilash", "/clear", "/reset"]:
        return

    user_id = message.from_user.id
    user_prompt = message.text

    # 1. Freemium balance limit checks
    lim_cfg = db.get_limit_config()
    limit_enabled = lim_cfg.get("limit_enabled", True) if lim_cfg else True
    bonus = lim_cfg.get("bonus_credits", 5) if lim_cfg else 5
    
    user = db.get_user(user_id)
    user_credits = user.get("message_credits", 0) if user else 0

    if limit_enabled and user_credits <= 0:
        bot_info = await message.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
        
        paywall_text = (
            "⚠️ **Kechirasiz, sizning bepul xabarlar limitingiz tugadi!**\n\n"
            "Botdan foydalanishda davom etish uchun do'stlaringizni taklif qiling. "
            f"Har bir taklif qilingan do'stingiz uchun sizga **+{bonus} ta** bepul xabar limiti qo'shiladi.\n\n"
            f"Sizning taklif havolangiz:\n`{ref_link}`"
        )
        await message.answer(paywall_text, parse_mode="Markdown")
        return

    # 2. Process credits decrement if limit is active
    if limit_enabled:
        db.deduct_credit(user_id)

    # Show Typing chat action
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    # Call AI API
    ai_reply, tokens_used = await get_ai_response(user_id=user_id, user_message=user_prompt)

    # Update stats
    db.increment_messages(user_id=user_id, tokens=tokens_used)

    # Append Global Footer if configured
    global_footer = db.get_footer()
    if global_footer:
        final_reply = f"{ai_reply}\n\n{global_footer}"
    else:
        final_reply = ai_reply

    # Send response back with robust markdown fallback
    try:
        await message.answer(final_reply, parse_mode="Markdown")
    except Exception as e:
        logger.warning(f"Markdown parse error, sending plain text. Details: {e}")
        try:
            await message.answer(final_reply)
        except Exception as err:
            logger.error(f"Failed to send plain text message: {err}")
