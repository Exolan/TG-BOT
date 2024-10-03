import aiomysql
import logging

class Database:
    def __init__(self, host, user, password, db, port=3306):
        self.host = host
        self.user = user
        self.password = password
        self.db = db
        self.port = port
        self.pool = None

    async def connect(self):
        """Подключение к базе данных."""
        try:
            self.pool = await aiomysql.create_pool(
                host=self.host,
                user=self.user,
                password=self.password,
                db=self.db,
                port=self.port,
                autocommit=True,
            )
            logging.info("Подключение к базе данных установлено")
        except Exception as e:
            logging.error(f"Ошибка при подключении к базе данных: {e}")

    async def disconnect(self):
        """Закрытие соединения с базой данных."""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            logging.info("Соединение с базой данных закрыто")

    async def execute(self, query, params=None):
        """Выполнение INSERT/UPDATE/DELETE запросов."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(query, params)
                    await conn.commit()
                    logging.info(f"Выполнен запрос: {query} с параметрами: {params}")
        except Exception as e:
            logging.error(f"Ошибка выполнения запроса {query}: {e}")

    async def fetchall(self, query, params=None):
        """Выполнение SELECT запросов с возвратом всех данных."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(query, params)
                    result = await cur.fetchall()
                    logging.info(f"Выполнен запрос: {query} с параметрами: {params}")
                    return result
        except Exception as e:
            logging.error(f"Ошибка выполнения запроса {query}: {e}")
            return None

    async def fetchone(self, query, params=None):
        """Выполнение SELECT запросов с возвратом одной записи."""
        try:
            async with self.pool.acquire() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(query, params)
                    result = await cur.fetchone()
                    logging.info(f"Выполнен запрос: {query} с параметрами: {params}")
                    return result
        except Exception as e:
            logging.error(f"Ошибка выполнения запроса {query}: {e}")
            return None

# Пример использования
async def main():
    db = Database(host="localhost", user="root", password="password", db="tgbot")
    await db.connect()

    # Пример запроса
    users = await db.fetchall("SELECT * FROM Users")
    print(users)

    await db.disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
