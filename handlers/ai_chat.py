import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states.states import AIChatState
from keyboards.reply import get_cancel_menu, get_main_menu
from external_api import get_ai_response, clear_history, rolling_history
from database import db

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("ai"))
@router.message(F.text == "🤖 AI bilan Suhbat")
async def enter_ai_chat(message: Message, state: FSMContext):
    """
    Triggers FSM context to enter AIChatState.chatting.
    Informs user they are chatting with DeepSeek.
    """
    await state.set_state(AIChatState.chatting)
    await message.answer(
        text=(
            "🤖 *DeepSeek AI bilan suhbat boshlandi!*\n\n"
            "Menga xohlagan savolingizni yuborishingiz mumkin. "
            "Suhbatdan chiqish uchun quyidagi *❌ Bekor qilish* tugmasini bosing."
        ),
        reply_markup=get_cancel_menu(),
        parse_mode="Markdown"
    )

@router.message(Command("clear"))
@router.message(F.text == "🔄 Suhbatni Yangilash")
async def clear_chat_history(message: Message, state: FSMContext):
    """
    Clears user's rolling chat history in RAM cache.
    """
    user_id = message.from_user.id
    clear_history(user_id)
    
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
    Shows metrics about the current rolling history in RAM.
    """
    user_id = message.from_user.id
    history_list = rolling_history.get(user_id, [])
    
    # Divide by 2 to count "turns" (user + assistant)
    turns_count = len(history_list) // 2
    messages_count = len(history_list)
    
    await message.answer(
        text=(
            f"🔍 *Savollar Tarixi (RAM):*\n\n"
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
    Displays typing indicator, calls DeepSeek API, appends global footer,
    and updates RAM metrics.
    """
    # Prevent handling button click texts as prompts
    if message.text in ["❌ Bekor qilish", "🔄 Suhbatni Yangilash", "/clear"]:
        return

    user_id = message.from_user.id
    user_prompt = message.text

    # Show Typing chat action
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    # Call DeepSeek API
    ai_reply, tokens_used = await get_ai_response(user_id=user_id, user_message=user_prompt)

    # Increment stats in RAM database (No sync here to avoid Rate Limits)
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
