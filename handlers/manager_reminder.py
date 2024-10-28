from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from states import AddReminderEmployeeState
from kb import main_keyboard, reminder_actions_keyboard
from db import Database
from aiogram import Bot
from aiogram3_calendar import SimpleCalendar, simple_cal_callback
from datetime import datetime
from utils import delete_old_messages, add_message_to_user, is_user_manager
from emoji import emojize

mreminders_router = Router()

@mreminders_router.message(lambda message: message.text == "Напоминания сотрудников")
async def employees_reminders_handler(msg: Message, db: Database, bot: Bot):
    user_id = msg.from_user.id

    await delete_old_messages(bot, db, user_id, msg.chat.id)

    # Проверяем, является ли пользователь начальником отдела
    if not await is_user_manager(user_id, db):
        await msg.answer(emojize(":red_exclamation_mark:")+"  У вас нет прав для просмотра напоминаний сотрудников")
        return

    # Запрашиваем сотрудников отдела начальника
    query = """
        SELECT user_id, user_fio 
        FROM Users 
        WHERE user_depart = (SELECT user_depart FROM Users WHERE user_id = %s) 
        AND user_id != %s
    """
    
    employees = await db.fetchall(query, (user_id, user_id))  # Передаем оба параметра


    # Если сотрудников нет
    if not employees:
        mes = await msg.answer(emojize(":red_exclamation_mark:")+"  В вашем отделе нет сотрудников")
        await add_message_to_user(db, user_id, mes)
        return

    # Отправляем сообщение для каждого сотрудника с кнопкой "Посмотреть"
    for employee in employees:
        inline_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Посмотреть", callback_data=f"view_emp_{employee['user_id']}"),
                 InlineKeyboardButton(text="Добавить", callback_data=f"add_rem_{employee['user_id']}")
                 ]
                
            ]
        )
        empl_mes = await msg.answer(f"Сотрудник: {employee['user_fio']}", reply_markup=inline_kb)
        await add_message_to_user(db, user_id, empl_mes)

@mreminders_router.callback_query(lambda call: call.data.startswith("view_emp_"))
async def view_employee_reminders(call: CallbackQuery, db: Database, bot: Bot):
    user_id = call.from_user.id
    await delete_old_messages(bot, db, user_id, call.message.chat.id)
    employee_id = call.data.split("_")[2]

    # Запрос напоминаний для выбранного сотрудника
    query = """
    SELECT task_id, task_name, task_date, task_importance 
    FROM Tasks 
    WHERE task_user = %s AND task_from_admin = true
    """
    
    tasks = await db.fetchall(query, (employee_id,))  # Передаем ID сотрудника

    # Если напоминаний нет
    if not tasks:
        mes = await call.message.answer(emojize(":red_exclamation_mark:")+"  У этого сотрудника нет напоминаний от начальника")
        await add_message_to_user(db, user_id, mes)
        return

    # Отправляем напоминания с кнопками "Изменить" и "Удалить"
    for task in tasks:
        importance_emoji = emojize(":green_square:") if task['task_importance'] == 0 else emojize(":yellow_square:") if task['task_importance'] == 1 else emojize(":red_square:")
        
        task_message = await call.message.answer(
            f"{task['task_name']}\nДата: {task['task_date']}\nВажность: {importance_emoji}",
            reply_markup=reminder_actions_keyboard(task['task_id'])
        )
        await add_message_to_user(db, user_id, task_message)  # Сохраняем ID каждого сообщения с напоминанием

@mreminders_router.callback_query(lambda call: call.data.startswith("add_rem_"))
async def add_employee_reminder(call: CallbackQuery, db: Database, state: FSMContext):
    employee_id = call.data.split("_")[2]

    # Хэндлер для начала добавления напоминания
    buttons = [
        [KeyboardButton(text="Отмена")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    await call.message.answer(emojize(":writing_hand_light_skin_tone:")+"  Введите текст напоминания", reply_markup=keyboard)
    # Сохраняем ID сотрудника в состоянии
    await state.update_data(employee_id=employee_id)

    await state.set_state(AddReminderEmployeeState.waiting_for_employee_text)

    

# Хэндлер для обработки текста напоминания
@mreminders_router.message(AddReminderEmployeeState.waiting_for_employee_text)
async def process_employee_reminder_text(msg: Message, state: FSMContext, db: Database):
    reminder_text = msg.text

    # Проверяем, что текст не является командой отмены
    if reminder_text == "Отмена":
        await msg.answer(emojize(":check_mark_button:")+"  Действие отменено", reply_markup=await main_keyboard(msg.from_user.id, db))
        await state.clear()  # Очищаем состояние
        return

    # Сохраняем текст напоминания в состояние
    await state.update_data(reminder_text=reminder_text)

    # Запускаем календарь для выбора даты
    await show_employee_calendar(msg, state, db)

# Хэндлер для запуска календаря при добавлении напоминания сотруднику
async def show_employee_calendar(msg: Message, state: FSMContext, db: Database):
    user_id = msg.from_user.id
    
    # Текущая дата
    current_date = datetime.now()

    # Показать календарь, начиная с текущего месяца и текущей даты
    main_message = await msg.answer(emojize(":alarm_clock:")+"  Выберите дату", 
                                    reply_markup=await SimpleCalendar().start_calendar(
                                        year=current_date.year, 
                                        month=current_date.month
                                    ))
    
    await add_message_to_user(db, user_id, main_message)
    await state.set_state(AddReminderEmployeeState.waiting_for_employee_date)

# Хэндлер для обработки выбранной даты при добавлении напоминания сотруднику
@mreminders_router.callback_query(AddReminderEmployeeState.waiting_for_employee_date, simple_cal_callback.filter())  # Убираем state из декоратора
async def process_employee_calendar(callback_query: CallbackQuery, db: Database, callback_data: dict, state: FSMContext, bot: Bot):
    buttons = [
        [KeyboardButton(text="Отмена")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    user_id = callback_query.from_user.id
    # Обрабатываем выбор даты с помощью SimpleCalendar
    result = await SimpleCalendar().process_selection(callback_query, callback_data)

    # Распаковываем результат
    selected_successful, selected_date = result

    if selected_successful:
        current_datetime = datetime.now()
        current_date = current_datetime.date()
        current_time = current_datetime.time()

        # Приводим selected_date к типу date
        selected_date_only = selected_date.date()

       # Проверяем, что выбранная дата не является прошедшей
        if selected_date_only < current_date:
            wrong_mes = await callback_query.message.answer(emojize(":red_exclamation_mark:")+"  Нельзя выбрать прошедшую дату. Попробуйте еще раз.")
            
            await delete_old_messages(bot, db, callback_query.from_user.id, callback_query.message.chat.id)
            await add_message_to_user(db, user_id, wrong_mes)
            # Повторно показываем календарь
            calendar_mes = await callback_query.message.answer(emojize(":alarm_clock:")+"  Выберите дату", reply_markup=await SimpleCalendar().start_calendar())
            await add_message_to_user(db, user_id, calendar_mes)
            return

        # Если выбранная дата — это сегодня
        if selected_date_only == current_date:
            # Проверяем текущее время
            if current_time.hour >= 18:
                wrong_mes = await callback_query.message.answer(emojize(":red_exclamation_mark:")+"  Нельзя выбрать сегодняшнюю дату после 18:00. Попробуйте еще раз.")
                
                await delete_old_messages(bot, db, callback_query.from_user.id, callback_query.message.chat.id)
                await add_message_to_user(db, user_id, wrong_mes)
                # Повторно показываем календарь
                calendar_mes = await callback_query.message.answer(emojize(":alarm_clock:")+"  Выберите дату", reply_markup=await SimpleCalendar().start_calendar())
                await add_message_to_user(db, user_id, calendar_mes)
                return

        await delete_old_messages(bot, db, callback_query.from_user.id, callback_query.message.chat.id)
        # Сохраняем выбранную дату в состояние
        await state.update_data(reminder_date=selected_date)

        # После выбора даты предлагаем выбрать важность
        importance_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Низкая", callback_data="empl_importance_0")],
                [InlineKeyboardButton(text="Средняя", callback_data="empl_importance_1")],
                [InlineKeyboardButton(text="Высокая", callback_data="empl_importance_2")],
            ]
        )

        main_message = await callback_query.message.answer(emojize(":warning:")+"  Выберите важность:", reply_markup=importance_keyboard)
        await add_message_to_user(db, user_id, main_message)

        cancel_message = await callback_query.message.answer(emojize(":red_exclamation_mark:")+'  Вы можете отменить действие, нажав на "Отмена"', reply_markup=keyboard)
        await add_message_to_user(db, user_id, cancel_message)

        await state.set_state(AddReminderEmployeeState.waiting_for_employee_importance)
    else:
        await callback_query.message.answer(emojize(":red_exclamation_mark:")+"  Дата не выбрана, попробуйте еще раз")

# Хэндлер для обработки выбора важности при добавлении напоминания сотруднику
@mreminders_router.callback_query(lambda call: call.data.startswith("empl_importance_"))
async def process_employee_importance(call: CallbackQuery, state: FSMContext, db: Database, bot: Bot):
    importance_level = int(call.data.split("_")[2])
    await delete_old_messages(bot, db, call.from_user.id, call.message.chat.id)

    # Получаем данные из состояния
    data = await state.get_data()
    reminder_text = data.get("reminder_text")
    reminder_date = data.get("reminder_date")
    employee_id = data.get("employee_id")
    print("Напоминание для сотрудника" + employee_id)

    if not reminder_text or not reminder_date:
        await call.message.answer(emojize(":red_exclamation_mark:")+emojize(":red_exclamation_mark:")+emojize(":red_exclamation_mark:")+"  Произошла ошибка. Попробуйте добавить напоминание заново.")
        await state.clear()
        return
    
    # Преобразуем дату в строку (в формате, совместимом с вашей базой данных)
    if isinstance(reminder_date, datetime):
        reminder_date_str = reminder_date.strftime('%Y-%m-%d')
    else:
        reminder_date_str = str(reminder_date)
        
    # Вставляем задачу в базу данных с указанием, что напоминание от начальника
    query = "INSERT INTO Tasks (task_name, task_date, task_importance, task_user, task_from_admin) VALUES (%s, %s, %s, %s, %s)"
    try:
        await db.execute(query, (reminder_text, reminder_date_str, importance_level, employee_id, True))
        await call.message.answer(emojize(":check_mark_button:")+"  Напоминание успешно добавлено!", reply_markup=await main_keyboard(call.from_user.id, db))
    except Exception as e:
        await call.message.answer(f"Ошибка добавления напоминания: {e}", reply_markup=await main_keyboard(call.from_user.id, db))
    finally:
        # Очищаем состояние после завершения добавления
        await state.clear()
