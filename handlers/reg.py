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

reg_router = Router()

# Обработка нажатия на кнопку "Регистрация"
@reg_router.message(lambda message: message.text == "Регистрация")
async def start_registration(msg: types.Message, state: FSMContext):
    await msg.answer("Как вас зовут?")
    await state.set_state(RegistrationState.waiting_for_fio)

# Получаем ФИО
@reg_router.message(RegistrationState.waiting_for_fio)
async def process_fio(msg: types.Message, state: FSMContext, db: Database):
    await state.update_data(fio=msg.text)
    
    # Запрашиваем отделы
    await msg.answer("Выберите ваш отдел", reply_markup=await department_buttons(db))
    await state.set_state(RegistrationState.waiting_for_department)
# Функция для получения списка отделов из БД и создания кнопок
async def department_buttons(db: Database):
    departments = await db.fetchall("SELECT depart_id, depart_name FROM Department")
    
    buttons = []

    # Создаем кнопки для каждого отдела
    for department in departments:
        buttons.append([KeyboardButton(text=department['depart_name'])])  # Изменено

    # Создаем клавиатуру с кнопками
    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,  # Обернули в список, чтобы создать одну строку
        resize_keyboard=True
    )

    return keyboard


# Обработка выбора отдела
@reg_router.message(RegistrationState.waiting_for_department)
async def process_department(msg: types.Message, state: FSMContext, db: Database):
    department_name = msg.text
    
    # Ищем отдел в базе данных
    department = await db.fetchone("SELECT depart_id FROM Department WHERE depart_name = %s", (department_name,))
    
    if department:
        await state.update_data(department_id=department['depart_id'])
        
        # Выбор роли
        await msg.answer("Вы сотрудник или начальник?", reply_markup=role_buttons())
        await state.set_state(RegistrationState.waiting_for_role)
    else:
        await msg.answer("Такого отдела не существует. Попробуйте снова.")

# Кнопки для выбора роли (Сотрудник или Начальник)
def role_buttons():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Сотрудник"), KeyboardButton(text="Начальник")]
        ], resize_keyboard=True
    )

# Обработка выбора роли и запрос пароля
@reg_router.message(RegistrationState.waiting_for_role)
async def process_role(msg: types.Message, state: FSMContext):
    user_role = msg.text.lower()
    data = await state.get_data()
    
    if user_role == "сотрудник":
        await state.update_data(role="admin")
        await msg.answer("Введите пароль для сотрудников.")
        await state.set_state(RegistrationState.waiting_for_password)
    elif user_role == "начальник":
        await state.update_data(role="manager")
        await msg.answer("Введите пароль для начальников.")
        await state.set_state(RegistrationState.waiting_for_password)
    else:
        await msg.answer("Пожалуйста, выберите 'Сотрудник' или 'Начальник'.")

# Проверка пароля при регистрации
@reg_router.message(RegistrationState.waiting_for_password)
async def process_registration_password(msg: types.Message, state: FSMContext, db: Database):
    user_password = msg.text
    data = await state.get_data()
    department_id = data['department_id']
    role = data['role']
    
    if role == "admin":
        query = "SELECT admin_password FROM Department WHERE depart_id = %s"
    else:
        query = "SELECT manager_password FROM Department WHERE depart_id = %s"

    result = await db.fetchone(query, (department_id,))
    stored_password = result['admin_password'] if role == "admin" else result['manager_password']

    if user_password == stored_password:
        # Регистрация пользователя
        user_id = msg.from_user.id
        user_fio = data['fio']
        await db.execute(
            "INSERT INTO Users (user_id, user_fio, user_depart) VALUES (%s, %s, %s)",
            (user_id, user_fio, department_id)
        )
        
        await msg.answer(f"Регистрация успешна! Добро пожаловать, {user_fio}!", reply_markup=main_keyboard())
        await state.clear()
    else:
        await msg.answer("Неверный пароль. Попробуйте снова.")