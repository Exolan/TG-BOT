from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from utils import is_user_manager

async def main_keyboard(user_id: int, db) -> ReplyKeyboardMarkup:
    buttons = [
        [
            KeyboardButton(text="Напоминания"),
            KeyboardButton(text="Помощь")
        ]
    ]

    # Проверяем, является ли пользователь начальником отдела
    if await is_user_manager(user_id, db):
        buttons.append([KeyboardButton(text="Напоминания сотрудников")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

def reminders_keyboard(user_id):
    buttons = [
        [
            KeyboardButton(text="Добавить"),
            KeyboardButton(text="Назад")
        ]
    ]

    # Создаем клавиатуру с добавленными кнопками
    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )
    return keyboard


def reminder_actions_keyboard(reminder_id):
    # Создаем клавиатуру и сразу добавляем кнопки
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Изменить", callback_data=f"edit_{reminder_id}")],
            [InlineKeyboardButton(text="Удалить", callback_data=f"delete_{reminder_id}")]
        ]
    )
    return keyboard