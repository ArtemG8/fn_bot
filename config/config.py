import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "investment_bot")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASS: str = os.getenv("DB_PASS", "")
    USDT_ADDRESS: str = os.getenv("USDT_ADDRESS", "")
    ADMIN_IDS: str = os.getenv("ADMIN_IDS", "")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "123")

# Создаем экземпляр конфигурации
conf = Config()
