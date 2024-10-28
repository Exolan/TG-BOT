from db import Database
from aiogram import Bot
from aiogram.types import Message
from datetime import datetime
from emoji import emojize
import config

async def send_message_date(bot: Bot, db: Database):
    """Отправляет сообщения пользователям, если текущая дата совпадает с датой задачи."""
    try:
        # Получаем текущую дату
        current_date = datetime.now().date()
        
        # Получаем задачи на текущую дату
        tasks = await db.fetchall(
            """
            SELECT t.task_name, t.task_date, t.task_importance, t.task_from_admin, u.user_id, u.user_fio
            FROM Tasks t
            JOIN Users u ON t.task_user = u.user_id
            WHERE t.task_date = %s
            """,
            (current_date,)
        )
        
        # Отправляем напоминания пользователям
        for task in tasks:
            user_id = task['user_id']
            task_description = f"{task['task_name']} (Важность: {task['task_importance']})"

            # Отправляем сообщение пользователю
            await bot.send_message(user_id, task_description)

            # Если задача от администратора, отправляем в групповой чат
            if task['task_from_admin']:
                await bot.send_message(
                    chat_id=config.ID_GROUP,  # ID вашего группового чата
                    text=f"{task_description}. Исполнитель: {task['user_fio']}"
                )
                
    except Exception as e:
        print(f"Ошибка при отправке напоминаний: {e}")

async def check_work(bot: Bot):
    """Проверка работы бота и отправка сообщения администратору."""
    try:
        await bot.send_message(config.ID_GROUP, 'Бот работает!')
    except Exception as e:
        print(f"Ошибка при отправке сообщения о статусе бота: {e}")


async def is_user_manager(user_id: int, db: Database) -> bool:
    """Проверяет, является ли пользователь начальником."""
    # Запрашиваем информацию о пользователе из базы данных
    user = await db.fetchone("SELECT user_depart FROM Users WHERE user_id = %s", (user_id,))
    
    if user:
        # Получаем идентификатор отдела пользователя
        department_id = user['user_depart']
        
        # Проверяем, является ли данный отдел начальником
        department = await db.fetchone("SELECT depart_name FROM Department WHERE depart_id = %s and depart_admin = %s", (department_id, user_id))
        
        if department:
            return True  # Пользователь является начальником
    return False  # Пользователь не является начальником


async def delete_old_messages(bot: Bot, db: Database, user_id: int, chat_id: int):
    # Получаем все сообщения пользователя
    query = "SELECT message_id FROM UserMessages WHERE user_id = %s"
    messages = await db.fetchall(query, (user_id,))
    
    if messages:
        for message in messages:
            message_id = message['message_id']
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
                print(f"Сообщение с ID {message_id} удалено.")
            except Exception as e:
                print(f"Ошибка при удалении сообщения {message_id}: {e}")

        # Удаляем записи из таблицы после удаления сообщений
        delete_query = "DELETE FROM UserMessages WHERE user_id = %s"
        await db.execute(delete_query, (user_id,))

async def add_message_to_user(db: Database, user_id: int, message: Message):
    print(user_id)
    # Извлекаем только идентификатор сообщения
    message_id = message.message_id

    query = """
        INSERT INTO UserMessages (user_id, message_id)
        VALUES (%s, %s)
    """
    await db.execute(query, (user_id, message_id))

