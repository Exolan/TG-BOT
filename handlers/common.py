from aiogram import types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from states import AddReminderState
from kb import main_keyboard
from db import Database
from aiogram import Bot
from utils import delete_old_messages
from handlers.reminder import reminders_handler
from emoji import emojize

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
    
    await msg.answer(emojize(":hand_with_fingers_splayed_light_skin_tone:")+"  Привет! Выберите действие", reply_markup=keyboard)

@common_router.message(lambda message: message.text == "Помощь")
async def help_handler(msg: Message):
    help_text = (
        "  Я еще не умею помогать"
    )
    await msg.answer(emojize(":face_with_monocle:")+help_text)

@common_router.message(lambda message: message.text == "Назад")
async def back_to_main_handler(msg: Message, state: FSMContext, db: Database):
    await state.clear()
    await msg.answer(emojize(":check_mark_button:")+"  Вы вернулись в главное меню", reply_markup=await main_keyboard(msg.from_user.id, db))

@common_router.message(lambda message: message.text == "Отмена")
async def process_cancel(msg: Message, state: FSMContext, db: Database, bot: Bot):
    current_state = await state.get_state()
    await msg.answer(emojize(":check_mark_button:")+"  Действие отменено", reply_markup=await main_keyboard(msg.from_user.id, db))


    await delete_old_messages(bot, db, msg.from_user.id, msg.chat.id)
    await state.clear()

    # Проверяем текущее состояние
    if current_state == AddReminderState.waiting_for_text or \
       current_state == AddReminderState.waiting_for_date or \
       current_state == AddReminderState.waiting_for_importance:
        # Если отмена в процессе добавления напоминания самому себе
        await reminders_handler(msg, db, bot)
