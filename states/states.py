from aiogram.fsm.state import StatesGroup, State

class ProfileSurvey(StatesGroup):
    """States for the user demographic registration survey."""
    gender = State()
    age = State()
    region = State()
    interest = State()

class SupportState(StatesGroup):
    """State for users sending questions/feedback to the admin."""
    waiting_for_message = State()

class AIChatState(StatesGroup):
    """State for active rolling AI conversation loop."""
    chatting = State()

class AdminState(StatesGroup):
    """States for admin operations."""
    waiting_for_footer = State()
    waiting_for_broadcast = State()
    waiting_for_limit_value = State()
