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
from utils import delete_old_messages, add_message_to_user

reminders_router = Router()

@reminders_router.message(lambda message: message.text == "Напоминания")
async def reminders_handler(msg: Message, db: Database, bot: Bot):
    user_id = msg.from_user.id

    await delete_old_messages(bot, db, user_id, msg.chat.id)
    query = "SELECT * FROM Tasks WHERE task_user = %s"
    tasks = await db.fetchall(query, (user_id,))

    # Если задач нет
    if not tasks:
        empty_message = await msg.answer("У вас нет напоминаний", reply_markup=reminders_keyboard(user_id))
        await add_message_to_user(db, user_id, empty_message)
        return

    # Отправляем сообщение о наличии напоминаний
    main_message = await msg.answer("Вот ваши напоминания", reply_markup=reminders_keyboard(user_id))

    await add_message_to_user(db, user_id, main_message)

    # Отправляем каждое напоминание и сохраняем его ID
    for task in tasks:
        task_message = await msg.answer(
            f"{task['task_name']}\nДата: {task['task_date']}\nВажность: {task['task_importance']}",
            reply_markup=reminder_actions_keyboard(task['task_id'])
        )
        await add_message_to_user(db, user_id, task_message)  # Сохраняем ID каждого сообщения с напоминанием

# Хэндлер для обработки нажатия на кнопку "Изменить"
@reminders_router.callback_query(lambda call: call.data.startswith("edit_"))
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

@reminders_router.message(lambda message: message.text == "Отмена")
async def process_cancle(msg: Message, state: FSMContext, db: Database, bot: Bot):
    await msg.answer("Действие отменено", reply_markup=main_keyboard())
    await delete_old_messages(bot, db, msg.from_user.id, msg.chat.id)
    await state.clear()  # Очищаем состояние

    # Перерисовываем все напоминания
    await reminders_handler(msg, db, bot)

# Хэндлер для обработки нового текста напоминания
@reminders_router.message(EditTaskState.waiting_for_text)
async def process_new_reminder_text(msg: Message, state: FSMContext, db: Database, bot: Bot):
    new_text = msg.text

    if new_text == "Отмена":
        return

    # Получаем ID напоминания из состояния
    data = await state.get_data()
    reminder_id = data.get("reminder_id")

    # Обновляем напоминание в базе данных
    await db.execute("UPDATE Tasks SET task_name = %s WHERE task_id = %s", (new_text, reminder_id))

    # Уведомляем пользователя об успешном изменении
    await msg.answer(f"Напоминание было успешно изменено")

    # Очищаем состояние
    await state.clear()

    await delete_old_messages(bot, db, msg.from_user.id, msg.chat.id)

    # Перерисовываем все напоминания
    await reminders_handler(msg, db, bot)

@reminders_router.callback_query(lambda call: call.data.startswith("delete_"))
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
@reminders_router.message(lambda message: message.text == "Удалить")
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

    await delete_old_messages(bot, db, msg.from_user.id, msg.chat.id)

    # Перерисовываем все напоминания
    await reminders_handler(msg, db, bot)

# Хэндлер для начала добавления напоминания
@reminders_router.message(lambda message: message.text == "Добавить")
async def add_reminder_handler(msg: Message, state: FSMContext):
    buttons = [
        [KeyboardButton(text="Отмена")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    await msg.answer("Введите текст напоминания", reply_markup=keyboard)
    await state.set_state(AddReminderState.waiting_for_text)

# Хэндлер для обработки текста напоминания
@reminders_router.message(AddReminderState.waiting_for_text)
async def process_reminder_text(msg: Message, state: FSMContext, db: Database):
    reminder_text = msg.text

    # Проверяем, что текст не является командой отмены
    if reminder_text == "Отмена":
        await msg.answer("Действие отменено", reply_markup=main_keyboard())
        await state.clear()  # Очищаем состояние
        return

    # Сохраняем текст напоминания в состояние
    await state.update_data(reminder_text=reminder_text)

    # Запускаем календарь для выбора даты
    await show_calendar(msg, state, db)

# Хэндлер для запуска календаря при добавлении напоминания
async def show_calendar(msg: Message, state: FSMContext, db: Database):
    user_id = msg.from_user.id
    # Показать календарь
    main_message = await msg.answer("Выберите дату:", reply_markup=await SimpleCalendar().start_calendar())
    
    await add_message_to_user(db, user_id, main_message)

    await state.set_state(AddReminderState.waiting_for_date)

# Хэндлер для обработки выбранной даты
@reminders_router.callback_query(simple_cal_callback.filter())
async def process_calendar(callback_query: CallbackQuery, db: Database, callback_data: dict, state: FSMContext):
    buttons = [
        [KeyboardButton(text="Отмена")]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    user_id = callback_query.from_user.id
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

        main_message = await callback_query.message.answer("Выберите важность:", reply_markup=importance_keyboard)
        await add_message_to_user(db, user_id, main_message)

        # Отправляем сообщение с возможностью отмены
        cancel_message = await callback_query.message.answer('Вы можете отменить действие, нажав на "Отмена"', reply_markup=keyboard)

        await add_message_to_user(db, user_id, cancel_message)

        await state.set_state(AddReminderState.waiting_for_importance)
    else:
        await callback_query.message.answer("Дата не выбрана, попробуйте еще раз.")

# Хэндлер для обработки выбора важности
@reminders_router.callback_query(lambda call: call.data.startswith("importance_"))
async def process_importance(call: CallbackQuery, state: FSMContext, db: Database, bot: Bot):
    importance_level = int(call.data.split("_")[1])
    await delete_old_messages(bot, db, call.from_user.id, call.message.chat.id)

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
        await call.message.answer("Напоминание успешно добавлено!", reply_markup=main_keyboard())
    except Exception as e:
        await call.message.answer(f"Ошибка добавления напоминания: {e}", reply_markup=main_keyboard())
    finally:
        # Очищаем состояние после завершения добавления
        await state.clear()
        # Перерисовываем все напоминания
        await delete_old_messages(bot, db, call.message.from_user.id, call.message.chat.id)
