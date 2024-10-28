from aiogram import types, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from states import RegistrationState
from kb import main_keyboard
from db import Database
from emoji import emojize

reg_router = Router()

# Обработка нажатия на кнопку "Регистрация"
@reg_router.message(lambda message: message.text == "Регистрация")
async def start_registration(msg: types.Message, state: FSMContext):
    # Если пользователь найден, запрашиваем пароль для отдела с кнопкой "Отмена"
    cancel_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отменить регистрацию")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await msg.answer(emojize(":red_question_mark:")+"  Как вас зовут?", reply_markup=cancel_keyboard)
    await state.set_state(RegistrationState.waiting_for_fio)

# Обработка нажатия на кнопку "Отменить регистрацию" в процессе регистрации
@reg_router.message(lambda message: message.text == "Отменить регистрацию")
async def cancel_registration(msg: types.Message, state: FSMContext):
    await state.clear()  # Сброс состояния регистрации

    # Клавиатура с кнопками "Вход" и "Регистрация"
    buttons = [
        [KeyboardButton(text="Вход"), KeyboardButton(text="Регистрация")]
    ]
    keyboard = ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )
    
    await msg.answer(emojize(":hand_with_fingers_splayed_light_skin_tone:")+"  Регистрация отменена. Выберите действие", reply_markup=keyboard)

# Получаем ФИО
@reg_router.message(RegistrationState.waiting_for_fio)
async def process_fio(msg: types.Message, state: FSMContext, db: Database):
    await state.update_data(fio=msg.text)
    
    # Запрашиваем отделы
    await msg.answer(emojize(":warning:")+"  Выберите ваш отдел", reply_markup=await department_buttons(db))
    await state.set_state(RegistrationState.waiting_for_department)
# Функция для получения списка отделов из БД и создания кнопок
async def department_buttons(db: Database):
    departments = await db.fetchall("SELECT depart_id, depart_name FROM Department")
    
    buttons = []

    # Создаем кнопки для каждого отдела
    for department in departments:
        buttons.append([KeyboardButton(text=department['depart_name'])])  # Изменено

    buttons.append([KeyboardButton(text="Отменить регистрацию")])

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
        await msg.answer(emojize(":red_question_mark:")+"  Вы сотрудник или начальник?", reply_markup=role_buttons())
        await state.set_state(RegistrationState.waiting_for_role)
    else:
        await msg.answer(emojize(":red_exclamation_mark:")+"  Такого отдела не существует. Попробуйте снова")

# Кнопки для выбора роли (Сотрудник или Начальник)
def role_buttons():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Сотрудник"), KeyboardButton(text="Начальник"), KeyboardButton(text="Отменить регистрацию")]
        ], resize_keyboard=True
    )

# Обработка выбора роли и запрос пароля
@reg_router.message(RegistrationState.waiting_for_role)
async def process_role(msg: types.Message, state: FSMContext):
    user_role = msg.text.lower()
    data = await state.get_data()
    
    if user_role == "сотрудник":
        await state.update_data(role="manager")
        await msg.answer(emojize(":writing_hand_light_skin_tone:")+"  Введите пароль для сотрудников")
        await state.set_state(RegistrationState.waiting_for_password)
    elif user_role == "начальник":
        await state.update_data(role="admin")
        await msg.answer(emojize(":writing_hand_light_skin_tone:")+"  Введите пароль для начальников")
        await state.set_state(RegistrationState.waiting_for_password)
    else:
        await msg.answer(emojize(":red_exclamation_mark:")+"  Пожалуйста, выберите 'Сотрудник' или 'Начальник'")

@reg_router.message(RegistrationState.waiting_for_password)
async def process_registration_password(msg: types.Message, state: FSMContext, db: Database):
    user_password = msg.text
    data = await state.get_data()
    department_id = data['department_id']
    role = data['role']
    
    if role == "admin":
        query = "SELECT admin_password, depart_admin FROM Department WHERE depart_id = %s"
    else:
        query = "SELECT manager_password FROM Department WHERE depart_id = %s"

    result = await db.fetchone(query, (department_id,))
    
    if result is None:
        await msg.answer(emojize(":red_exclamation_mark:")+"  Отдел не найден. Проверьте ваши данные.")
        return

    stored_password = result['admin_password'] if role == "admin" else result['manager_password']

    if user_password == stored_password:
        # Регистрация пользователя
        user_id = msg.from_user.id
        user_fio = data['fio']
        
        # Проверка наличия начальника в отделе
        if role == "admin" and result['depart_admin'] is None:
            # Если начальника нет, записываем его ID
            await db.execute(
                "UPDATE Department SET depart_admin = %s WHERE depart_id = %s",
                (user_id, department_id)
            )

        await db.execute(
            "INSERT INTO Users (user_id, user_fio, user_depart) VALUES (%s, %s, %s)",
            (user_id, user_fio, department_id)
        )
        
        await msg.answer(emojize(":check_mark_button:")+"  Регистрация успешна! Добро пожаловать, " + user_fio + "!", reply_markup= await main_keyboard(msg.from_user.id, db))
        await state.clear()
    else:
        await msg.answer(emojize(":red_exclamation_mark:")+"  Неверный пароль. Попробуйте снова.")