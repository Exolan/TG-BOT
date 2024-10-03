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

router = Router()


########################################## АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ #############################################

# Приветствие при старте бота
@router.message(Command("start"))
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

# Обработка нажатия на кнопку "Вход"
@router.message(lambda message: message.text == "Вход")
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
@router.message(AuthState.waiting_for_password)
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

# Обработка нажатия на кнопку "Регистрация"
@router.message(lambda message: message.text == "Регистрация")
async def start_registration(msg: types.Message, state: FSMContext):
    await msg.answer("Как вас зовут?")
    await state.set_state(RegistrationState.waiting_for_fio)

# Получаем ФИО
@router.message(RegistrationState.waiting_for_fio)
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
@router.message(RegistrationState.waiting_for_department)
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
@router.message(RegistrationState.waiting_for_role)
async def process_role(msg: types.Message, state: FSMContext):
    user_role = msg.text.lower()
    data = await state.get_data()
    
    if user_role == "сотрудник":
        await state.update_data(role="employee")
        await msg.answer("Введите пароль для сотрудников.")
        await state.set_state(RegistrationState.waiting_for_password)
    elif user_role == "начальник":
        await state.update_data(role="manager")
        await msg.answer("Введите пароль для начальников.")
        await state.set_state(RegistrationState.waiting_for_password)
    else:
        await msg.answer("Пожалуйста, выберите 'Сотрудник' или 'Начальник'.")

# Проверка пароля при регистрации
@router.message(RegistrationState.waiting_for_password)
async def process_registration_password(msg: types.Message, state: FSMContext, db: Database):
    user_password = msg.text
    data = await state.get_data()
    department_id = data['department_id']
    role = data['role']
    
    if role == "employee":
        query = "SELECT employee_password FROM Department WHERE depart_id = %s"
    else:
        query = "SELECT manager_password FROM Department WHERE depart_id = %s"

    result = await db.fetchone(query, (department_id,))
    stored_password = result['employee_password'] if role == "employee" else result['manager_password']

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

########################################## ОСНОВНОЙ ФУНКЦИОНАЛ #############################################

@router.message(lambda message: message.text == "Назад")
async def back_to_main_handler(msg: Message, state: FSMContext,):
    await state.clear()
    await msg.answer("Вы вернулись в главное меню", reply_markup=main_keyboard())

# Словарь для хранения ID сообщений с напоминаниями для каждого пользователя
user_messages = {}

@router.message(lambda message: message.text == "Напоминания")
async def reminders_handler(msg: Message, db: Database, bot: Bot):
    user_id = msg.from_user.id
    query = "SELECT * FROM Tasks WHERE task_user = %s"
    tasks = await db.fetchall(query, (user_id,))

    # Удаляем старые сообщения с напоминаниями, если они есть
    if user_id in user_messages and user_messages[user_id]:
        for message_id in user_messages[user_id]:
            try:
                await bot.delete_message(chat_id=msg.chat.id, message_id=message_id)  # Используем msg.bot
            except Exception as e:
                print(f"Ошибка при удалении сообщения: {e}")  # Логирование ошибки при удалении
        user_messages[user_id].clear()

    # Если задач нет
    if not tasks:
        empty_message = await msg.answer("У вас нет напоминаний", reply_markup=reminders_keyboard(user_id))
        user_messages[user_id] = [empty_message.message_id]  # Сохраняем ID сообщения о пустом списке
        return

    # Отправляем сообщение о наличии напоминаний
    main_message = await msg.answer("Вот ваши напоминания", reply_markup=reminders_keyboard(user_id))
    user_messages[user_id] = [main_message.message_id]  # Сохраняем ID основного сообщения

    # Отправляем каждое напоминание и сохраняем его ID
    for task in tasks:
        task_message = await msg.answer(
            f"{task['task_name']}\nДата: {task['task_date']}\nВажность: {task['task_importance']}",
            reply_markup=reminder_actions_keyboard(task['task_id'])
        )
        user_messages[user_id].append(task_message.message_id)  # Сохраняем ID каждого сообщения с напоминанием

# Хэндлер для обработки нажатия на кнопку "Изменить"
@router.callback_query(lambda call: call.data.startswith("edit_"))
async def edit_reminder_callback(call: CallbackQuery, state: FSMContext):
    reminder_id = call.data.split("_")[1]  # Извлекаем ID напоминания из callback_data

    # Сохраняем ID задачи в состоянии
    await state.update_data(reminder_id=reminder_id)

    # Создаем кнопки для отправки нового текста и отмены
    buttons = [
        [KeyboardButton(text="Отмена")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

    # Запрашиваем новый текст напоминания
    await call.message.answer("Отправьте новый текст напоминания", reply_markup=keyboard)
    await state.set_state(EditTaskState.waiting_for_text)  # Переключаем в состояние ожидания нового текста

# Хэндлер для обработки нового текста напоминания
@router.message(EditTaskState.waiting_for_text)
async def process_new_reminder_text(msg: Message, state: FSMContext, db: Database, bot: Bot):
    new_text = msg.text

    # Получаем ID напоминания из состояния
    data = await state.get_data()
    reminder_id = data.get("reminder_id")

    # Обновляем напоминание в базе данных
    await db.execute("UPDATE Tasks SET task_name = %s WHERE task_id = %s", (new_text, reminder_id))

    # Уведомляем пользователя об успешном изменении
    await msg.answer(f"Напоминание было успешно изменено")

    # Очищаем состояние
    await state.clear()

    # Перерисовываем все напоминания
    await reminders_handler(msg, db, bot)

@router.callback_query(lambda call: call.data.startswith("delete_"))
async def delete_reminder_callback(call: CallbackQuery, state: FSMContext):
    reminder_id = call.data.split("_")[1]
    
    # Сохраняем ID задачи в состоянии
    await state.update_data(reminder_id=reminder_id)

    # Создаем обычные кнопки для подтверждения удаления
    buttons = [
        [KeyboardButton(text="Удалить")],
        [KeyboardButton(text="Отмена")]
    ]

    # Создаем клавиатуру с обычными кнопками
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)

    # Запрашиваем подтверждение удаления
    await call.message.answer("Вы уверены, что хотите удалить напоминание?", reply_markup=keyboard)

# Хэндлер для обработки ответа "Удалить"
@router.message(lambda message: message.text == "Удалить")
async def process_delete_task(msg: Message, state: FSMContext, db: Database, bot: Bot):
    # Получаем ID напоминания из состояния
    data = await state.get_data()
    reminder_id = data.get("reminder_id")

    # Удаляем напоминание из базы данных
    await db.execute("DELETE FROM Tasks WHERE task_id = %s", (reminder_id,))

    # Уведомляем пользователя об успешном удалении
    await msg.answer(f"Напоминание было успешно удалено")
    # Очищаем состояние
    await state.clear()

    # Перерисовываем все напоминания
    await reminders_handler(msg, db, bot)

@router.message(lambda message: message.text == "Отмена")
async def process_cancle(msg: Message, state: FSMContext, db: Database, bot: Bot):
    await msg.answer("Действие отменено", reply_markup=main_keyboard())
    await state.clear()  # Очищаем состояние
    # Перерисовываем все напоминания
    await reminders_handler(msg, db, bot)

# Хэндлер для начала добавления напоминания
@router.message(lambda message: message.text == "Добавить")
async def add_reminder_handler(msg: Message, state: FSMContext):
    await msg.answer("Введите текст напоминания")
    await state.set_state(AddReminderState.waiting_for_text)

# Хэндлер для обработки текста напоминания
@router.message(AddReminderState.waiting_for_text)
async def process_reminder_text(msg: Message, state: FSMContext):
    reminder_text = msg.text
    await state.update_data(reminder_text=reminder_text)
    
    # Переключаем состояние и запускаем календарь
    await show_calendar(msg, state)

# Хэндлер для запуска календаря при добавлении напоминания
async def show_calendar(msg: Message, state: FSMContext):
    # Показать календарь
    await msg.answer("Выберите дату:", reply_markup=await SimpleCalendar().start_calendar())
    await state.set_state(AddReminderState.waiting_for_date)

# Хэндлер для обработки выбранной даты
@router.callback_query(simple_cal_callback.filter())
async def process_calendar(callback_query: CallbackQuery, callback_data: dict, state: FSMContext):
    result = await SimpleCalendar().process_selection(callback_query, callback_data)  # Необходимо использовать await!

    # Распаковываем результат
    selected_successful, selected_date = result

    if selected_successful:
        # Сохраняем выбранную дату в состояние
        await state.update_data(reminder_date=selected_date)

        # После выбора даты предлагаем выбрать важность
        importance_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
            [InlineKeyboardButton(text="Низкая", callback_data="importance_0")],
            [InlineKeyboardButton(text="Средняя", callback_data="importance_1")],
            [InlineKeyboardButton(text="Высокая", callback_data="importance_2")],
            ]
        )
            

        await callback_query.message.answer("Выберите важность:", reply_markup=importance_keyboard)
        await state.set_state(AddReminderState.waiting_for_importance)
    else:
        await callback_query.message.answer("Дата не выбрана, попробуйте еще раз.")

# Хэндлер для обработки выбора важности
@router.callback_query(lambda call: call.data.startswith("importance_"))
async def process_importance(call: CallbackQuery, state: FSMContext, db: Database):
    importance_level = int(call.data.split("_")[1])

    # Получаем данные из состояния
    data = await state.get_data()
    reminder_text = data.get("reminder_text")
    reminder_date = data.get("reminder_date")

    if not reminder_text or not reminder_date:
        await call.message.answer("Произошла ошибка. Попробуйте добавить напоминание заново.")
        await state.clear()
        return
    
    # Преобразуем дату в строку (в формате, совместимом с вашей базой данных)
    if isinstance(reminder_date, datetime):
        reminder_date_str = reminder_date.strftime('%Y-%m-%d')
    else:
        reminder_date_str = str(reminder_date)
        
    # Вставляем задачу в базу данных
    query = "INSERT INTO Tasks (task_name, task_date, task_importance, task_user) VALUES (%s, %s, %s, %s)"
    try:
        await db.execute(query, (reminder_text, reminder_date_str, importance_level, call.from_user.id))
        await call.message.answer("Напоминание успешно добавлено!")
    except Exception as e:
        await call.message.answer(f"Ошибка добавления напоминания: {e}")
    finally:
        # Очищаем состояние после завершения добавления
        await state.clear()

@router.message(lambda message: message.text == "Добавить сотруднику")
async def add_subordinate_reminder_handler(msg: Message):
    await msg.answer("Отправьте ID подчиненного и текст напоминания в формате: ID текст напоминания")

@router.message(lambda message: message.text == "Помощь")
async def help_handler(msg: Message):
    help_text = (
        "Вот как можно использовать бота:\n"
        "- Добавить напоминание: Нажмите 'Добавить напоминание' и отправьте текст напоминания\n"
        "- Изменить напоминание: Нажмите 'Изменить напоминание' и отправьте ID и новый текст напоминания\n"
        "- Удалить напоминание: Нажмите 'Удалить напоминание' и отправьте ID напоминания для удаления\n"
        "- Помощь: Нажмите 'Помощь' для получения этого сообщения"
    )
    await msg.answer(help_text)