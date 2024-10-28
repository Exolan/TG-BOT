from aiogram import types, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from states import AuthState
from kb import main_keyboard
from db import Database
from emoji import emojize
from handlers.common import start_handler

auth_router = Router()

# Обработка нажатия на кнопку "Вход"
@auth_router.message(lambda message: message.text == "Вход")
async def login_handler(msg: types.Message, state: FSMContext, db: Database):
    user_id = msg.from_user.id

    # Проверяем, существует ли пользователь в базе
    user = await db.fetchone("SELECT * FROM Users WHERE user_id = %s", (user_id,))
    
    if not user:
        # Если пользователя с таким user_id нет в базе
        await msg.answer(emojize(":red_exclamation_mark:")+"  Вы не зарегистрированы. Пожалуйста, зарегистрируйтесь через кнопку 'Регистрация'")
        return

    # Если пользователь найден, запрашиваем пароль для отдела с кнопкой "Отмена"
    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отменить вход")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await msg.answer(emojize(":writing_hand_light_skin_tone:")+"  Введите пароль", reply_markup=cancel_keyboard)
    await state.set_state(AuthState.waiting_for_password)

# Обработка пароля при входе
@auth_router.message(AuthState.waiting_for_password)
async def process_login_password(msg: types.Message, state: FSMContext, db: Database):
    user_password = msg.text
    user_id = msg.from_user.id

    # Обработка нажатия кнопки "Отменить вход"
    if user_password == "Отменить вход":
        await state.clear()
        await start_handler(msg)  # Вызываем стартовое меню с кнопками "Вход" и "Регистрация"
        return
    
    # Получаем информацию о пользователе, включая отдел
    user = await db.fetchone("SELECT u.user_fio, d.depart_name, d.admin_password, d.manager_password "
                             "FROM Users u JOIN Department d ON u.user_depart = d.depart_id WHERE u.user_id = %s", (user_id,))
    
    if not user:
        await msg.answer(emojize(":red_exclamation_mark:")+"  Ошибка при получении данных пользователя. Попробуйте позже")
        return

    # Сравниваем введенный пароль с паролями отдела (сотрудник или начальник)
    if user_password == user['admin_password'] or user_password == user['manager_password']:
        # Успешная авторизация
        await msg.answer(emojize(":hand_with_fingers_splayed_light_skin_tone:")+"  Добро пожаловать, " + user['user_fio'] + "! Вы вошли в " + user['depart_name'], reply_markup=await main_keyboard(msg.from_user.id, db))
        await state.clear()
    else:
        # Неверный пароль
        await msg.answer(emojize(":red_exclamation_mark:")+"  Неверный пароль. Попробуйте снова")