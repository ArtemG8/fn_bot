from decimal import Decimal


def format_balance(balance: Decimal) -> str:
    """
    Форматирует баланс, убирая лишние нули.
    Если баланс пустой или равен 0, возвращает "0 $"
    Без научной нотации (не 1E+2, а 100).
    """
    if balance is None:
        return "0 $"
    
    balance_decimal = Decimal(str(balance))
    
    if balance_decimal == 0:
        return "0 $"
    
    # Формат 'f' — обычная запись, без научной нотации; убираем лишние нули
    balance_str = format(balance_decimal, '.10f').rstrip('0').rstrip('.')
    
    return f"{balance_str} $"
