from database.connection import db


async def create_tables():
    """Создает все необходимые таблицы в базе данных"""
    
    # Таблица пользователей
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username VARCHAR(255),
            full_name VARCHAR(255),
            balance DECIMAL(20, 8) DEFAULT 0,
            referral_code VARCHAR(50) UNIQUE,
            referred_by BIGINT REFERENCES users(user_id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_admin BOOLEAN DEFAULT FALSE,
            usdt_address VARCHAR(255)
        )
    """)
    
    # Таблица депозитов
    await db.execute("""
        CREATE TABLE IF NOT EXISTS deposits (
            deposit_id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            amount DECIMAL(20, 8) NOT NULL,
            interest_rate DECIMAL(5, 2) NOT NULL,
            current_balance DECIMAL(20, 8) DEFAULT 0,
            status VARCHAR(20) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_accrual_date DATE,
            total_earned DECIMAL(20, 8) DEFAULT 0
        )
    """)
    
    # Таблица транзакций
    await db.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            transaction_type VARCHAR(50) NOT NULL,
            amount DECIMAL(20, 8) NOT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deposit_id INTEGER REFERENCES deposits(deposit_id),
            admin_id BIGINT
        )
    """)
    
    # Таблица реферальных начислений
    await db.execute("""
        CREATE TABLE IF NOT EXISTS referral_bonuses (
            bonus_id SERIAL PRIMARY KEY,
            referrer_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            referred_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            amount DECIMAL(20, 8) NOT NULL,
            transaction_id INTEGER REFERENCES transactions(transaction_id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица настроек админки
    await db.execute("""
        CREATE TABLE IF NOT EXISTS admin_settings (
            setting_key VARCHAR(50) PRIMARY KEY,
            setting_value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Инициализация пароля админки, если его нет
    existing_password = await db.fetchval(
        "SELECT setting_value FROM admin_settings WHERE setting_key = 'admin_password'"
    )
    if not existing_password:
        from config.config import conf
        await db.execute(
            """INSERT INTO admin_settings (setting_key, setting_value) 
               VALUES ('admin_password', $1) 
               ON CONFLICT (setting_key) DO NOTHING""",
            conf.ADMIN_PASSWORD
        )
    
    # Индексы для оптимизации
    await db.execute("CREATE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_deposits_user_id ON deposits(user_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_deposits_status ON deposits(status)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_referral_bonuses_referrer ON referral_bonuses(referrer_id)")
