from aiogram import Bot
from aiogram.types import BotCommand


async def set_main_menu(bot: Bot):
    """Устанавливает главное меню бота"""
    main_menu_commands = [
        BotCommand(command='start', description='🚀 Начать работу'),
        BotCommand(command='profile', description='👤 Профиль'),
        BotCommand(command='balance', description='💰 Баланс'),
        BotCommand(command='deposits', description='📈 Депозиты'),
        BotCommand(command='topup', description='💳 Пополнить'),
        BotCommand(command='withdraw', description='💸 Вывести'),
        BotCommand(command='referral', description='👥 Реферальная программа'),
    ]
    await bot.set_my_commands(main_menu_commands)
