from aiogram import types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from states import RegistrationState, AuthState, EditTaskState, AddReminderState
from kb import main_keyboard, reminders_keyboard, reminder_actions_keyboard
from db import Database
from aiogram import Bot
from aiogram3_calendar import SimpleCalendar, simple_cal_callback
from datetime import datetime

common_router = Router()

# Приветствие при старте бота
@common_router.message(Command("start"))
async def start_handler(msg: types.Message):
    buttons = [
        [
            KeyboardButton(text="Вход"), KeyboardButton(text="Регистрация")
        ]
    ]
    # Создаем клавиатуру с добавленными кнопками
    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )
    
    await msg.answer("Привет! Выберите действие:", reply_markup=keyboard)

@common_router.message(lambda message: message.text == "Помощь")
async def help_handler(msg: Message):
    help_text = (
        "Вот как можно использовать бота:\n"
        "- Добавить напоминание: Нажмите 'Добавить напоминание' и отправьте текст напоминания\n"
        "- Изменить напоминание: Нажмите 'Изменить напоминание' и отправьте ID и новый текст напоминания\n"
        "- Удалить напоминание: Нажмите 'Удалить напоминание' и отправьте ID напоминания для удаления\n"
        "- Помощь: Нажмите 'Помощь' для получения этого сообщения"
    )
    await msg.answer(help_text)

@common_router.message(lambda message: message.text == "Назад")
async def back_to_main_handler(msg: Message, state: FSMContext,):
    await state.clear()
    await msg.answer("Вы вернулись в главное меню", reply_markup=main_keyboard())