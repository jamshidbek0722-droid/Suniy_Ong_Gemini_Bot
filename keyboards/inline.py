from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import config

def get_fsub_keyboard() -> InlineKeyboardMarkup:
    """
    Generates forced subscription inline keyboard.
    Displays buttons for all required channels and a verification button.
    """
    builder = InlineKeyboardBuilder()
    for channel in config.REQUIRED_CHANNELS:
        builder.row(
            InlineKeyboardButton(text=f"📢 {channel['name']}", url=channel['url'])
        )
    builder.row(
        InlineKeyboardButton(text="✅ Obunani Tekshirish", callback_data="check_sub")
    )
    return builder.as_markup()

def get_gender_keyboard() -> InlineKeyboardMarkup:
    """
    Returns inline buttons for Gender selection.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Erkak 🧑", callback_data="gender_Erkak"),
        InlineKeyboardButton(text="Ayol 👩", callback_data="gender_Ayol")
    )
    return builder.as_markup()

def get_region_keyboard() -> InlineKeyboardMarkup:
    """
    Returns a grid keyboard for selecting a region of Uzbekistan.
    """
    regions = [
        "Toshkent sh.", "Toshkent v.", "Andijon v.", "Buxoro v.",
        "Farg'ona v.", "Jizzax v.", "Xorazm v.", "Namangan v.",
        "Navoiy v.", "Qashqadaryo v.", "Samarqand v.", "Sirdaryo v.",
        "Surxondaryo v.", "Qoraqalpog'iston R."
    ]
    builder = InlineKeyboardBuilder()
    for reg in regions:
        builder.button(text=reg, callback_data=f"reg_{reg}")
    builder.adjust(2)  # Two columns layout
    return builder.as_markup()

def get_profile_keyboard(completed: bool = False) -> InlineKeyboardMarkup:
    """
    Keyboard for profile view to start/restart profile survey.
    """
    builder = InlineKeyboardBuilder()
    btn_text = "📝 Profilni Qayta To'ldirish" if completed else "📝 AI Profilni To'ldirish"
    builder.row(
        InlineKeyboardButton(text=btn_text, callback_data="fill_profile")
    )
    return builder.as_markup()

def get_support_keyboard() -> InlineKeyboardMarkup:
    """
    Keyboard for Settings/Help displaying Support contact trigger.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✍️ Adminga savol yo'llash", callback_data="contact_admin")
    )
    return builder.as_markup()
