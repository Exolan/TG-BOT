from db import Database
from aiogram import Bot
from aiogram.types import Message

async def is_user_manager(user_id: int, db: Database) -> bool:
    """Проверяет, является ли пользователь начальником."""
    # Запрашиваем информацию о пользователе из базы данных
    user = await db.fetchone("SELECT user_depart FROM Users WHERE user_id = %s", (user_id,))
    
    if user:
        # Получаем идентификатор отдела пользователя
        department_id = user['user_depart']
        
        # Проверяем, является ли данный отдел начальником
        department = await db.fetchone("SELECT manager_password FROM Department WHERE depart_id = %s", (department_id,))
        
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

