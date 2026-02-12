"""
Воркер для ежедневных начислений по депозитам
Запускается отдельным процессом или через cron
"""
import asyncio
import logging
from datetime import datetime
from database.connection import db
from services.accruals import calculate_daily_accruals
from config.config import conf

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_accruals():
    """Запускает процесс начислений"""
    try:
        # Подключаемся к БД
        await db.create_pool()
        logger.info("Database connection established")
        
        # Выполняем начисления
        logger.info("Starting daily accruals calculation...")
        result = await calculate_daily_accruals()
        
        logger.info(
            f"Accruals completed: {result['accruals_count']} deposits, "
            f"total amount: {result['total_accrued']} USDT"
        )
        
    except Exception as e:
        logger.error(f"Error during accruals: {e}", exc_info=True)
    finally:
        await db.close_pool()


if __name__ == '__main__':
    asyncio.run(run_accruals())
