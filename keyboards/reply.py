from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_menu() -> ReplyKeyboardMarkup:
    """
    Returns the tech-themed main menu keyboard.
    Row 1: [🤖 AI bilan Suhbat] (Standalone Premium Action)
    Row 2: [🔄 Suhbatni Yangilash] | [🔍 Savollar Tarixi]
    Row 3: [👤 Mening Profilim] | [⚙️ Sozlamalar / Yordam]
    """
    keyboard = [
        [KeyboardButton(text="🤖 AI bilan Suhbat")],
        [
            KeyboardButton(text="🔄 Suhbatni Yangilash"),
            KeyboardButton(text="🔍 Savollar Tarixi")
        ],
        [
            KeyboardButton(text="👤 Mening Profilim"),
            KeyboardButton(text="⚙️ Sozlamalar / Yordam")
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        persistent=True,
        input_field_placeholder="Kerakli bo'limni tanlang..."
    )

def get_cancel_menu() -> ReplyKeyboardMarkup:
    """
    Returns a reply keyboard with only the cancel button.
    Used during FSM states or active AI chat sessions.
    """
    keyboard = [
        [KeyboardButton(text="❌ Bekor qilish")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Suhbatni to'xtatish uchun bosing..."
    )

def get_admin_menu() -> ReplyKeyboardMarkup:
    """
    Returns the admin actions menu.
    """
    keyboard = [
        [
            KeyboardButton(text="📊 Analitika Panel"),
            KeyboardButton(text="📢 Footer O'zgartirish")
        ],
        [
            KeyboardButton(text="⚙️ Limitlarni Sozlash"),
            KeyboardButton(text="📢 Reklama Jo'natish")
        ],
        [KeyboardButton(text="❌ Bekor qilish")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Admin bo'limi..."
    )
