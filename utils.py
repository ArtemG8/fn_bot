from decimal import Decimal


def format_balance(balance: Decimal) -> str:
    """
    Форматирует баланс, убирая лишние нули.
    Если баланс пустой или равен 0, возвращает "0 $"
    """
    if balance is None:
        return "0 $"
    
    # Преобразуем Decimal в float для нормализации, затем обратно в Decimal
    balance_decimal = Decimal(str(balance))
    
    if balance_decimal == 0:
        return "0 $"
    
    # Нормализуем Decimal (убираем лишние нули)
    balance_normalized = balance_decimal.normalize()
    
    # Преобразуем в строку
    balance_str = str(balance_normalized)
    
    return f"{balance_str} $"
