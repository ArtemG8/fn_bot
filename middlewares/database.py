from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable
from database.connection import db


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для проверки подключения к БД"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if not db.pool:
            await db.create_pool()
        return await handler(event, data)
