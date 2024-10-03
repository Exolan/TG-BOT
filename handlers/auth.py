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

auth_router = Router()

# Обработка нажатия на кнопку "Вход"
@auth_router.message(lambda message: message.text == "Вход")
async def login_handler(msg: types.Message, state: FSMContext, db: Database):
    user_id = msg.from_user.id

    # Проверяем, существует ли пользователь в базе
    user = await db.fetchone("SELECT * FROM Users WHERE user_id = %s", (user_id,))
    
    if not user:
        # Если пользователя с таким user_id нет в базе
        await msg.answer("Вы не зарегистрированы. Пожалуйста, зарегистрируйтесь через кнопку 'Регистрация'.")
        return

    # Если пользователь найден, запрашиваем пароль для отдела
    await msg.answer("Введите пароль:")
    await state.set_state(AuthState.waiting_for_password)

# Обработка пароля при входе
@auth_router.message(AuthState.waiting_for_password)
async def process_login_password(msg: types.Message, state: FSMContext, db: Database):
    user_password = msg.text
    user_id = msg.from_user.id
    
    # Получаем информацию о пользователе, включая отдел
    user = await db.fetchone("SELECT u.user_fio, d.depart_name, d.employee_password, d.manager_password "
                             "FROM Users u JOIN Department d ON u.user_depart = d.depart_id WHERE u.user_id = %s", (user_id,))
    
    if not user:
        await msg.answer("Ошибка при получении данных пользователя.")
        return

    # Сравниваем введенный пароль с паролями отдела (сотрудник или начальник)
    if user_password == user['employee_password'] or user_password == user['manager_password']:
        # Успешная авторизация
        await msg.answer(f"Добро пожаловать, {user['user_fio']}! Вы вошли в {user['depart_name']}.", reply_markup=main_keyboard())
        await state.clear()
    else:
        # Неверный пароль
        await msg.answer("Неверный пароль. Попробуйте снова.")