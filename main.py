import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from config.config import conf
from keyboards.set_menu import set_main_menu
from database.connection import db
from database.db import create_tables
from handlers import private_user, admin
from middlewares.database import DatabaseMiddleware

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(filename)s:%(lineno)d #%(levelname)-8s '
           '[%(asctime)s] - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Starting bot...")

    # Подключаемся к базе данных
    await db.create_pool()
    logger.info("Database connection established")

    # Создаем таблицы в БД, если их нет
    logger.info("Creating database tables if not exist...")
    await create_tables()
    logger.info("Database tables checked/created.")

    storage = MemoryStorage()

    # Инициализируем бота и диспетчера
    bot = Bot(token=conf.BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    dp = Dispatcher(storage=storage)

    # Регистрируем middleware
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())

    # Регистрируем роутеры
    dp.include_router(private_user.router)
    dp.include_router(admin.router)

    # Установка команд меню
    await set_main_menu(bot)

    # Пропускаем накопившиеся апдейты и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot is running...")
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")
    finally:
        # Закрываем соединение с БД
        asyncio.run(db.close_pool())