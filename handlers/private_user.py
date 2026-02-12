import secrets
from decimal import Decimal, InvalidOperation
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from database.connection import db
from database.models import User, Deposit, Transaction
from lexicon.lexicon_ru import LEXICON_RU
from keyboards.keyboard_utils import (
    get_main_keyboard, get_deposit_keyboard, get_back_keyboard
)
from keyboards.flow_kb import get_cancel_keyboard
from states.states import DepositStates, TopUpStates, WithdrawStates
from config.config import conf

router = Router()

# Константы
MIN_DEPOSIT = Decimal('10')
MIN_TOPUP = Decimal('10')
REFERRAL_BONUS_PERCENT = Decimal('5')  # 5% от суммы депозита реферала
DEFAULT_INTEREST_RATE = Decimal('1')  # 1% в день
USDT_ADDRESS = conf.USDT_ADDRESS or "TYourUSDTAddressHere"


async def get_or_create_user(user_id: int, username: str = None, full_name: str = None, referred_by: int = None) -> User:
    """Получает пользователя из БД или создает нового"""
    user = await db.fetchrow(
        "SELECT * FROM users WHERE user_id = $1",
        user_id
    )
    
    if user:
        return User.from_row(user)
    
    # Генерируем уникальный реферальный код
    referral_code = secrets.token_urlsafe(8)[:8].upper()
    while await db.fetchval("SELECT user_id FROM users WHERE referral_code = $1", referral_code):
        referral_code = secrets.token_urlsafe(8)[:8].upper()
    
    await db.execute(
        """INSERT INTO users (user_id, username, full_name, referral_code, referred_by)
           VALUES ($1, $2, $3, $4, $5)""",
        user_id, username, full_name, referral_code, referred_by
    )
    
    # Если пользователь пришел по реферальной ссылке, начисляем бонус рефереру
    if referred_by:
        referrer = await db.fetchrow("SELECT * FROM users WHERE user_id = $1", referred_by)
        if referrer:
            # Можно добавить небольшой бонус за регистрацию реферала
            pass
    
    return await get_or_create_user(user_id, username, full_name, referred_by)


@router.message(Command('start'))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    
    # Проверяем реферальный код
    referred_by = None
    if len(message.text.split()) > 1:
        ref_code = message.text.split()[1]
        referrer = await db.fetchrow(
            "SELECT user_id FROM users WHERE referral_code = $1",
            ref_code
        )
        if referrer:
            referred_by = referrer['user_id']
    
    user = await get_or_create_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
        referred_by
    )
    
    await message.answer(
        LEXICON_RU['start'],
        reply_markup=get_main_keyboard()
    )


@router.message(F.text == "👤 Профиль")
@router.message(Command('profile'))
async def cmd_profile(message: Message):
    """Показывает профиль пользователя"""
    user = await get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    
    # Подсчитываем активные депозиты
    active_deposits = await db.fetchval(
        "SELECT COUNT(*) FROM deposits WHERE user_id = $1 AND status = 'active'",
        message.from_user.id
    ) or 0
    
    # Подсчитываем рефералов
    referrals_count = await db.fetchval(
        "SELECT COUNT(*) FROM users WHERE referred_by = $1",
        message.from_user.id
    ) or 0
    
    await message.answer(
        LEXICON_RU['profile'].format(
            balance=user.balance,
            active_deposits=active_deposits,
            referrals_count=referrals_count,
            referral_code=user.referral_code
        )
    )


@router.message(F.text == "💰 Баланс")
@router.message(Command('balance'))
async def cmd_balance(message: Message):
    """Показывает баланс пользователя"""
    user = await get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    await message.answer(
        LEXICON_RU['balance'].format(balance=user.balance)
    )


@router.message(F.text == "📈 Депозиты")
@router.message(Command('deposits'))
async def cmd_deposits(message: Message):
    """Меню депозитов"""
    await message.answer(
        LEXICON_RU['deposit_menu'],
        reply_markup=get_deposit_keyboard()
    )


@router.callback_query(F.data == "create_deposit")
async def create_deposit_callback(callback: CallbackQuery, state: FSMContext):
    """Начало создания депозита"""
    await callback.message.edit_text(
        LEXICON_RU['create_deposit'],
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(DepositStates.waiting_for_amount)
    await callback.answer()


@router.message(StateFilter(DepositStates.waiting_for_amount))
async def process_deposit_amount(message: Message, state: FSMContext):
    """Обработка суммы депозита"""
    try:
        amount = Decimal(message.text.replace(',', '.'))
        
        if amount < MIN_DEPOSIT:
            await message.answer(
                LEXICON_RU['invalid_amount'].format(min=MIN_DEPOSIT)
            )
            return
        
        user = await get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
        
        if user.balance < amount:
            await message.answer(LEXICON_RU['not_enough_balance'])
            return
        
        # Создаем депозит
        deposit_id = await db.fetchval(
            """INSERT INTO deposits (user_id, amount, interest_rate, current_balance, status)
               VALUES ($1, $2, $3, $4, 'active')
               RETURNING deposit_id""",
            message.from_user.id, amount, DEFAULT_INTEREST_RATE, amount
        )
        
        # Списываем средства с баланса
        await db.execute(
            "UPDATE users SET balance = balance - $1 WHERE user_id = $2",
            amount, message.from_user.id
        )
        
        # Создаем транзакцию
        await db.execute(
            """INSERT INTO transactions (user_id, transaction_type, amount, status, description, deposit_id)
               VALUES ($1, 'deposit_created', $2, 'completed', 'Создание депозита', $3)""",
            message.from_user.id, amount, deposit_id
        )
        
        # Начисляем реферальный бонус, если есть реферер
        if user.referred_by:
            bonus_amount = amount * REFERRAL_BONUS_PERCENT / 100
            await db.execute(
                "UPDATE users SET balance = balance + $1 WHERE user_id = $2",
                bonus_amount, user.referred_by
            )
            await db.execute(
                """INSERT INTO referral_bonuses (referrer_id, referred_id, amount)
                   VALUES ($1, $2, $3)""",
                user.referred_by, message.from_user.id, bonus_amount
            )
        
        await message.answer(
            LEXICON_RU['deposit_created'].format(
                amount=amount,
                rate=DEFAULT_INTEREST_RATE
            ),
            reply_markup=get_main_keyboard()
        )
        await state.clear()
        
    except (ValueError, InvalidOperation):
        await message.answer("❌ Неверный формат суммы. Введите число, например: 100")


@router.callback_query(F.data == "list_deposits")
async def list_deposits_callback(callback: CallbackQuery):
    """Список депозитов пользователя"""
    deposits = await db.fetch(
        "SELECT * FROM deposits WHERE user_id = $1 ORDER BY created_at DESC",
        callback.from_user.id
    )
    
    if not deposits:
        await callback.message.edit_text(
            LEXICON_RU['no_deposits'],
            reply_markup=get_back_keyboard()
        )
        await callback.answer()
        return
    
    deposits_text = ""
    for dep in deposits:
        deposits_text += f"\n💼 Депозит #{dep['deposit_id']}\n"
        deposits_text += f"Сумма: {dep['amount']} USDT\n"
        deposits_text += f"Баланс: {dep['current_balance']} USDT\n"
        deposits_text += f"Ставка: {dep['interest_rate']}% в день\n"
        deposits_text += f"Заработано: {dep['total_earned']} USDT\n"
        deposits_text += f"Статус: {dep['status']}\n"
    
    await callback.message.edit_text(
        LEXICON_RU['deposit_list'].format(deposits=deposits_text),
        reply_markup=get_back_keyboard()
    )
    await callback.answer()


@router.message(F.text == "💳 Пополнить")
@router.message(Command('topup'))
async def cmd_topup(message: Message, state: FSMContext):
    """Пополнение баланса"""
    await message.answer(
        LEXICON_RU['top_up'].format(address=USDT_ADDRESS),
        reply_markup=get_main_keyboard()
    )


@router.message(F.text == "💸 Вывести")
@router.message(Command('withdraw'))
async def cmd_withdraw(message: Message, state: FSMContext):
    """Вывод средств"""
    await message.answer(
        LEXICON_RU['withdraw'],
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(WithdrawStates.waiting_for_amount)


@router.message(StateFilter(WithdrawStates.waiting_for_amount))
async def process_withdraw_amount(message: Message, state: FSMContext):
    """Обработка суммы вывода"""
    try:
        amount = Decimal(message.text.replace(',', '.'))
        user = await get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
        
        if user.balance < amount:
            await message.answer(LEXICON_RU['not_enough_balance'])
            return
        
        if amount < Decimal('10'):
            await message.answer(LEXICON_RU['invalid_amount'].format(min=10))
            return
        
        await state.update_data(withdraw_amount=amount)
        await message.answer(
            LEXICON_RU['withdraw_address'],
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(WithdrawStates.waiting_for_address)
        
    except (ValueError, InvalidOperation):
        await message.answer("❌ Неверный формат суммы. Введите число, например: 100")


@router.message(StateFilter(WithdrawStates.waiting_for_address))
async def process_withdraw_address(message: Message, state: FSMContext):
    """Обработка адреса для вывода"""
    data = await state.get_data()
    amount = data['withdraw_amount']
    address = message.text.strip()
    
    # Простая валидация адреса TRC20 (начинается с T и имеет длину 34)
    if not (address.startswith('T') and len(address) == 34):
        await message.answer("❌ Неверный формат адреса USDT (TRC20). Адрес должен начинаться с T и иметь длину 34 символа.")
        return
    
    user = await get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    
    # Создаем транзакцию на вывод
    transaction_id = await db.fetchval(
        """INSERT INTO transactions (user_id, transaction_type, amount, status, description)
           VALUES ($1, 'withdraw', $2, 'pending', $3)
           RETURNING transaction_id""",
        message.from_user.id, amount, f"Вывод на адрес {address}"
    )
    
    # Резервируем средства (можно вычесть сразу или оставить на балансе до подтверждения)
    await db.execute(
        "UPDATE users SET balance = balance - $1 WHERE user_id = $2",
        amount, message.from_user.id
    )
    
    await message.answer(
        LEXICON_RU['withdraw_request'].format(
            amount=amount,
            address=address
        ),
        reply_markup=get_main_keyboard()
    )
    await state.clear()


@router.message(F.text == "👥 Реферальная программа")
@router.message(Command('referral'))
async def cmd_referral(message: Message):
    """Реферальная программа"""
    user = await get_or_create_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    
    referrals_count = await db.fetchval(
        "SELECT COUNT(*) FROM users WHERE referred_by = $1",
        message.from_user.id
    ) or 0
    
    total_bonuses = await db.fetchval(
        "SELECT COALESCE(SUM(amount), 0) FROM referral_bonuses WHERE referrer_id = $1",
        message.from_user.id
    ) or 0
    
    bot_username = (await message.bot.get_me()).username
    referral_link = LEXICON_RU['referral_link'].format(
        bot_username=bot_username,
        code=user.referral_code
    )
    
    text = LEXICON_RU['referral'].format(
        code=user.referral_code,
        count=referrals_count,
        bonuses=total_bonuses
    )
    text += f"\n\n🔗 Ваша реферальная ссылка:\n{referral_link}"
    
    await message.answer(text)


@router.callback_query(F.data == "back_to_main")
async def back_to_main_callback(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "Главное меню",
        reply_markup=None
    )
    await callback.message.answer(
        LEXICON_RU['start'],
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена действия"""
    await state.clear()
    await callback.message.edit_text("Действие отменено.")
    await callback.answer()
