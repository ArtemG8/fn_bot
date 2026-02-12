from decimal import Decimal
from datetime import date, datetime
from database.connection import db


async def calculate_daily_accruals():
    """Вычисляет и начисляет ежедневные проценты по всем активным депозитам"""
    today = date.today()
    
    # Получаем все активные депозиты
    deposits = await db.fetch(
        """SELECT * FROM deposits 
           WHERE status = 'active'"""
    )
    
    accruals_count = 0
    total_accrued = Decimal('0')
    
    for deposit in deposits:
        deposit_id = deposit['deposit_id']
        user_id = deposit['user_id']
        current_balance = deposit['current_balance']
        interest_rate = deposit['interest_rate']
        last_accrual_date = deposit['last_accrual_date']
        
        # Проверяем, нужно ли начислять сегодня
        if last_accrual_date and last_accrual_date >= today:
            continue
        
        # Вычисляем сумму начисления (процент от текущего баланса)
        accrual_amount = current_balance * interest_rate / 100
        
        # Обновляем баланс депозита
        new_balance = current_balance + accrual_amount
        await db.execute(
            """UPDATE deposits 
               SET current_balance = $1, 
                   last_accrual_date = $2,
                   total_earned = total_earned + $3
               WHERE deposit_id = $4""",
            new_balance, today, accrual_amount, deposit_id
        )
        
        # Начисляем проценты на баланс пользователя
        await db.execute(
            "UPDATE users SET balance = balance + $1 WHERE user_id = $2",
            accrual_amount, user_id
        )
        
        # Создаем транзакцию начисления
        await db.execute(
            """INSERT INTO transactions (user_id, transaction_type, amount, status, description, deposit_id)
               VALUES ($1, 'daily_accrual', $2, 'completed', 'Ежедневное начисление по депозиту', $3)""",
            user_id, accrual_amount, deposit_id
        )
        
        accruals_count += 1
        total_accrued += accrual_amount
    
    return {
        'accruals_count': accruals_count,
        'total_accrued': total_accrued
    }
