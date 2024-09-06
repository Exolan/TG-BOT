from aiogram import types, Router
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.types import Message   
from aiogram.types import CallbackQuery

import config
from states import UserState
from kb import main_keyboard, reminders_keyboard, reminder_actions_keyboard

router = Router()

@router.message(Command("start"))
async def start_handler(msg: Message):
    await msg.answer("Привет! Выберите действие", reply_markup=main_keyboard())

@router.message(Text("Назад"))
async def back_to_main_handler(msg: Message):
    await msg.answer("Вы вернулись в главное меню", reply_markup=main_keyboard())

@router.message(Text("Напоминания"))
async def reminders_handler(msg: Message):
    user_id = msg.from_user.id
    reminders = config.REMINDERS.get(user_id, [])

    if not reminders:
        await msg.answer("У вас нет напоминаний", reply_markup=reminders_keyboard(user_id))
        return

    await msg.answer("Вот ваши напоминания", reply_markup=reminders_keyboard(user_id))

    for i, reminder in enumerate(reminders, 1):
        await msg.answer(f"Напоминание {i}: {reminder}", reply_markup=reminder_actions_keyboard(i))


@router.message(Text("Добавить"))
async def add_reminder_handler(msg: Message):
    await msg.answer("Отправьте текст напоминания")
    # Установите состояние для ожидания текста напоминания, если используете FSM

@router.message(Text("Изменить"))
async def change_reminder_handler(msg: Message):
    await msg.answer("Отправьте ID напоминания и новый текст в формате: ID новый текст напоминания")

@router.message(Text("Удалить"))
async def delete_reminder_handler(msg: Message):
    await msg.answer("Отправьте ID напоминания для удаления")

@router.message(Text("Добавить сотруднику"))
async def add_subordinate_reminder_handler(msg: Message):
    await msg.answer("Отправьте ID подчиненного и текст напоминания в формате: ID текст напоминания")

@router.message(Text("Помощь"))
async def help_handler(msg: Message):
    help_text = (
        "Вот как можно использовать бота:\n"
        "- Добавить напоминание: Нажмите 'Добавить напоминание' и отправьте текст напоминания\n"
        "- Изменить напоминание: Нажмите 'Изменить напоминание' и отправьте ID и новый текст напоминания\n"
        "- Удалить напоминание: Нажмите 'Удалить напоминание' и отправьте ID напоминания для удаления\n"
        "- Помощь: Нажмите 'Помощь' для получения этого сообщения"
    )
    await msg.answer(help_text)

# Обработчик для кнопки "Удалить"
@router.callback_query(Text(startswith="delete_"))
async def delete_reminder_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    reminder_id = int(callback.data.split("_")[1]) - 1

    reminders = config.REMINDERS.get(user_id, [])
    
    if reminder_id < len(reminders):
        removed = reminders.pop(reminder_id)
        await callback.message.edit_text(f"Напоминание '{removed}' удалено.", reply_markup=None)
    else:
        await callback.answer("Ошибка: Напоминание не найдено.")

@router.message(UserState.waiting_for_reminder_text)
async def process_reminder(msg: Message, state: FSMContext):
    user_id = msg.from_user.id
    text = msg.text

    if user_id not in config.REMINDERS:
        config.REMINDERS[user_id] = []

    config.REMINDERS[user_id].append(text)
    await msg.answer("Ваше напоминание добавлено")
    await state.clear()
