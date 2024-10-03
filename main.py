import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
from handlers.common import common_router
from handlers.auth import auth_router
from handlers.reg import reg_router
from handlers.reminder import reminders_router
from db import Database  # Импортируем класс для работы с БД
from middleware import DatabaseMiddleware, BotMiddleware

# Инициализация подключения к базе данных
db = Database(
    host=config.DB_HOST,
    user=config.DB_USER,
    password=config.DB_PASSWORD,
    db=config.DB_NAME
)

async def main():
    # Подключаемся к базе данных
    await db.connect()

    bot = Bot(token=config.BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())

    # Добавляем middleware для передачи объекта базы данных
    dp.update.middleware(DatabaseMiddleware(db))
    dp.update.middleware(BotMiddleware(bot))

    dp.include_router(common_router)
    dp.include_router(auth_router)
    dp.include_router(reg_router)
    dp.include_router(reminders_router)

    # Уведомление о запуске бота
    logging.info("Бот успешно запущен и готов к работе")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

async def shutdown():
    # Закрытие соединения с базой данных при завершении работы бота
    await db.disconnect()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        asyncio.run(shutdown())  # Отключаемся от базы данных при завершении работы