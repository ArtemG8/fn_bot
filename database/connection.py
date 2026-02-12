import asyncpg
from config.config import conf


class Database:
    def __init__(self):
        self.pool: asyncpg.Pool = None

    async def create_pool(self):
        """Создает пул соединений с базой данных"""
        self.pool = await asyncpg.create_pool(
            host=conf.DB_HOST,
            port=int(conf.DB_PORT),
            database=conf.DB_NAME,
            user=conf.DB_USER,
            password=conf.DB_PASS,
            min_size=5,
            max_size=20
        )

    async def close_pool(self):
        """Закрывает пул соединений"""
        if self.pool:
            await self.pool.close()

    async def execute(self, query: str, *args):
        """Выполняет запрос без возврата результата"""
        async with self.pool.acquire() as conn:
            await conn.execute(query, *args)

    async def fetch(self, query: str, *args):
        """Выполняет запрос и возвращает все строки"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args):
        """Выполняет запрос и возвращает одну строку"""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        """Выполняет запрос и возвращает одно значение"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)


# Глобальный экземпляр базы данных
db = Database()
