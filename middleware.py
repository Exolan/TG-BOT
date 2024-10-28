from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from aiogram import Bot

class BotMiddleware(BaseMiddleware):
    def __init__(self, bot: Bot):
        self.bot = bot

        super().__init__()

    async def __call__(self, handler, event: TelegramObject, data: dict):
        # Добавляем bot в контекст
        data['bot'] = self.bot
        return await handler(event, data)

class DatabaseMiddleware(BaseMiddleware):
    def __init__(self, db):
        self.db = db
        super().__init__()

    async def __call__(self, handler, event: TelegramObject, data: dict):
        # Добавляем объект базы данных в данные хендлера
        data['db'] = self.db
        return await handler(event, data)
    
class AuthMiddleware(BaseMiddleware):
    def __init__(self, db):
        super().__init__()
        self.db = db

    async def __call__(self, handler, event: Message, data):
        user_id = event.from_user.id
        user = await self.db.fetchone("SELECT * FROM Users WHERE user_id = %s", (user_id,))
        
        if user is None and event.text not in ["Вход", "Регистрация", "/start"]:
            await event.answer("Пожалуйста, авторизуйтесь или зарегистрируйтесь, чтобы продолжить.")
            return  # Блокируем доступ
        
        return await handler(event, data)


