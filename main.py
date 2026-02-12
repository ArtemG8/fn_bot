import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from config import conf
from keyboards import set_main_menu

# Настройка логирования
logger = logging.getLogger(__name__)

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(filename)s:%(lineno)d #%(levelname)-8s '
               '[%(asctime)s] - %(name)s - %(message)s'
    )

    logger.info("Starting bot...")

    storage = MemoryStorage()

    # Инициализируем бота и диспетчера
    bot = Bot(token=conf.BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
    dp = Dispatcher(storage=storage)


    # Установка команд меню
    await set_main_menu(bot)

    # Создаем таблицы в БД, если их нет
    logger.info("Creating database tables if not exist...")
    await create_db_and_tables()
    logger.info("Database tables checked/created.")


    # Пропускаем накопившиеся апдейты и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped!")
