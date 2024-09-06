from aiogram.fsm.state import StatesGroup, State

class UserState(StatesGroup):
    waiting_for_reminder_text = State()
    waiting_for_id = State()
