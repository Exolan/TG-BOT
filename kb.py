from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import config

def main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Напоминания"),
                KeyboardButton(text="Помощь")
            ]
        ],
        resize_keyboard=True
    )

def reminders_keyboard(user_id):
    buttons = [
        [
            KeyboardButton(text="Добавить"),
        ]
    ]
    if user_id in config.MANAGERS:
        buttons.append([KeyboardButton(text="Добавить сотруднику")])

    buttons.append([KeyboardButton(text="Назад")])

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