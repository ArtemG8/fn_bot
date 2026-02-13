import os
from decimal import Decimal, InvalidOperation
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from database.connection import db
from lexicon.lexicon_ru import LEXICON_RU
from keyboards.keyboard_utils import (
    get_admin_keyboard, get_transaction_keyboard, get_back_keyboard,
    get_admin_back_keyboard, get_admin_settings_keyboard, get_cancel_reject_keyboard,
    get_cancel_news_keyboard
)
from states.states import AdminStates
from config.config import conf
from utils import format_balance

router = Router()

# ID администраторов (можно вынести в конфиг)
ADMIN_IDS = [int(id) for id in conf.ADMIN_IDS.split(",") if id] if conf.ADMIN_IDS else []


async def get_admin_password() -> str:
    """Получает пароль админки из БД или конфига"""
    password = await db.fetchval(
        "SELECT setting_value FROM admin_settings WHERE setting_key = 'admin_password'"
    )
    return password or conf.ADMIN_PASSWORD


async def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    if ADMIN_IDS and user_id in ADMIN_IDS:
        return True
    user = await db.fetchrow("SELECT is_admin FROM users WHERE user_id = $1", user_id)
    return user and user['is_admin']


@router.message(Command('admin'))
async def cmd_admin(message: Message, state: FSMContext):
    """Панель администратора - запрос пароля"""
    await message.answer(
        "🔐 Введите пароль для доступа к админ панели:",
        reply_markup=None
    )
    await state.set_state(AdminStates.waiting_for_password)


@router.message(StateFilter(AdminStates.waiting_for_password))
async def process_admin_password(message: Message, state: FSMContext):
    """Проверка пароля админки"""
    password = await get_admin_password()
    
    if message.text != password:
        await message.answer("❌ Неверный пароль. Попробуйте снова.")
        return
    
    # Пароль верный, показываем админ панель
    await message.answer(
        LEXICON_RU['admin_panel'],
        reply_markup=get_admin_keyboard()
    )
    await state.clear()


def format_datetime(dt) -> str:
    """Форматирует дату без секунд"""
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M")
    return str(dt)[:16] if len(str(dt)) > 16 else str(dt)


@router.callback_query(F.data == "admin_pending")
async def admin_pending_callback(callback: CallbackQuery, bot: Bot):
    """Список ожидающих транзакций"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    transactions = await db.fetch(
        """SELECT t.*, u.username, u.full_name 
           FROM transactions t
           JOIN users u ON t.user_id = u.user_id
           WHERE t.status = 'pending'
           ORDER BY t.created_at DESC
           LIMIT 20"""
    )
    
    if not transactions:
        await callback.message.edit_text(
            "✅ Нет ожидающих транзакций",
            reply_markup=get_admin_back_keyboard()
        )
        await callback.answer()
        return
    
    # Отправляем каждую транзакцию отдельным сообщением с кнопками
    await callback.message.edit_text(
        f"⏳ <b>Ожидающие транзакции</b>\n\nНайдено: {len(transactions)}",
        reply_markup=get_admin_back_keyboard()
    )
    
    for trans in transactions:
        username_display = f"@{trans['username']}" if trans['username'] else "без username"
        full_name_display = trans['full_name'] or "Не указано"
        
        transaction_text = (
            f"<b>Транзакция #{trans['transaction_id']}</b>\n\n"
            f"Тип: {trans['transaction_type']}\n"
            f"Пользователь: {full_name_display} ({username_display})\n"
            f"Сумма: {format_balance(trans['amount'])}\n"
            f"Описание: {trans['description'] or 'Не указано'}\n"
            f"Дата: {format_datetime(trans['created_at'])}"
        )
        
        await bot.send_message(
            callback.message.chat.id,
            transaction_text,
            reply_markup=get_transaction_keyboard(trans['transaction_id'])
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("approve_"))
async def approve_transaction_callback(callback: CallbackQuery, bot: Bot):
    """Одобрение транзакции"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    transaction_id = int(callback.data.split("_")[1])
    
    transaction = await db.fetchrow(
        "SELECT * FROM transactions WHERE transaction_id = $1",
        transaction_id
    )
    
    if not transaction:
        await callback.answer("❌ Транзакция не найдена", show_alert=True)
        return
    
    if transaction['status'] != 'pending':
        await callback.answer("❌ Транзакция уже обработана", show_alert=True)
        return
    
    # Если это пополнение, начисляем баланс и отправляем сообщение пользователю
    if transaction['transaction_type'] == 'topup':
        await db.execute(
            "UPDATE users SET balance = balance + $1 WHERE user_id = $2",
            transaction['amount'], transaction['user_id']
        )
        
        # Отправляем сообщение пользователю
        try:
            await bot.send_message(
                transaction['user_id'],
                f"✅ Ваш запрос на пополнение одобрен!\nНа ваш баланс зачислено {format_balance(transaction['amount'])}!"
            )
        except Exception:
            # Если не удалось отправить сообщение (пользователь заблокировал бота и т.д.)
            pass
    
    # Если это вывод средств, отправляем сообщение пользователю
    if transaction['transaction_type'] == 'withdraw':
        try:
            await bot.send_message(
                transaction['user_id'],
                f"✅ Ваш запрос на вывод средств одобрен!\n"
                f"Сумма: {format_balance(transaction['amount'])}\n"
                f"Средства будут переведены в ближайшее время."
            )
        except Exception:
            pass
    
    # Обновляем статус транзакции
    await db.execute(
        """UPDATE transactions 
           SET status = 'completed', admin_id = $1 
           WHERE transaction_id = $2""",
        callback.from_user.id, transaction_id
    )
    
    await callback.message.edit_text(
        f"✅ Транзакция #{transaction_id} одобрена",
        reply_markup=get_admin_back_keyboard()
    )
    await callback.answer("✅ Транзакция одобрена")


@router.callback_query(F.data.startswith("reject_"))
async def reject_transaction_callback(callback: CallbackQuery, state: FSMContext):
    """Начало процесса отклонения транзакции - запрос причины"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    transaction_id = int(callback.data.split("_")[1])
    
    transaction = await db.fetchrow(
        "SELECT * FROM transactions WHERE transaction_id = $1",
        transaction_id
    )
    
    if not transaction:
        await callback.answer("❌ Транзакция не найдена", show_alert=True)
        return
    
    if transaction['status'] != 'pending':
        await callback.answer("❌ Транзакция уже обработана", show_alert=True)
        return
    
    # Сохраняем ID транзакции в состоянии
    await state.update_data(reject_transaction_id=transaction_id)
    
    await callback.message.edit_text(
        f"❌ <b>Отклонение транзакции #{transaction_id}</b>\n\n"
        f"Введите причину отклонения (это сообщение будет отправлено пользователю):",
        reply_markup=get_cancel_reject_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_reject_reason)
    await callback.answer()


@router.callback_query(F.data == "cancel_reject")
async def cancel_reject_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена отклонения транзакции"""
    await state.clear()
    await callback.message.edit_text(
        "Отклонение транзакции отменено.",
        reply_markup=get_admin_back_keyboard()
    )
    await callback.answer()


@router.message(StateFilter(AdminStates.waiting_for_reject_reason))
async def process_reject_reason(message: Message, state: FSMContext, bot: Bot):
    """Обработка причины отклонения транзакции"""
    if not await is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        await state.clear()
        return
    
    data = await state.get_data()
    transaction_id = data.get('reject_transaction_id')
    
    if not transaction_id:
        await message.answer("❌ Ошибка: транзакция не найдена")
        await state.clear()
        return
    
    reason = message.text.strip()
    
    if not reason:
        await message.answer("❌ Причина не может быть пустой. Введите причину отклонения:")
        return
    
    transaction = await db.fetchrow(
        "SELECT * FROM transactions WHERE transaction_id = $1",
        transaction_id
    )
    
    if not transaction:
        await message.answer("❌ Транзакция не найдена")
        await state.clear()
        return
    
    if transaction['status'] != 'pending':
        await message.answer("❌ Транзакция уже обработана")
        await state.clear()
        return
    
    # Если это вывод, возвращаем средства на баланс
    if transaction['transaction_type'] == 'withdraw':
        await db.execute(
            "UPDATE users SET balance = balance + $1 WHERE user_id = $2",
            transaction['amount'], transaction['user_id']
        )
        
        # Отправляем сообщение пользователю с причиной
        try:
            await bot.send_message(
                transaction['user_id'],
                f"❌ Ваш запрос на вывод средств отклонен.\n\n"
                f"Сумма {format_balance(transaction['amount'])} возвращена на ваш баланс.\n\n"
                f"<b>Причина:</b> {reason}"
            )
        except Exception:
            pass
    
    # Если это пополнение, отправляем сообщение с причиной
    if transaction['transaction_type'] == 'topup':
        try:
            await bot.send_message(
                transaction['user_id'],
                f"❌ Ваш запрос на пополнение отклонен.\n\n"
                f"<b>Причина:</b> {reason}\n\n"
                f"Обратитесь к администратору для уточнения деталей."
            )
        except Exception:
            pass
    
    # Обновляем статус транзакции и сохраняем причину в описании
    await db.execute(
        """UPDATE transactions 
           SET status = 'rejected', admin_id = $1, description = $3
           WHERE transaction_id = $2""",
        message.from_user.id, transaction_id, f"{transaction['description'] or ''}\nПричина отклонения: {reason}"
    )
    
    await message.answer(
        f"✅ Транзакция #{transaction_id} отклонена.\nПричина отправлена пользователю.",
        reply_markup=get_admin_back_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "admin_add_balance")
async def admin_add_balance_callback(callback: CallbackQuery, state: FSMContext):
    """Добавление баланса пользователю"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "Введите username или user_id пользователя для начисления баланса:",
        reply_markup=get_admin_back_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_username)
    await callback.answer()


@router.message(StateFilter(AdminStates.waiting_for_username))
async def process_admin_username(message: Message, state: FSMContext):
    """Обработка username или user_id пользователя для начисления"""
    text = message.text.strip().lstrip('@')
    
    # Проверяем, является ли введенное значение числом (user_id)
    try:
        user_id = int(text)
        # Ищем по user_id
        user = await db.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        if not user:
            await message.answer(f"❌ Пользователь с ID {user_id} не найден")
            return
    except ValueError:
        # Не число, значит это username
        username = text
        user = await db.fetchrow("SELECT * FROM users WHERE username = $1", username)
        if not user:
            await message.answer(f"❌ Пользователь с username @{username} не найден")
            return
    
    await state.update_data(admin_user_id=user['user_id'])
    username_display = f"@{user['username']}" if user['username'] else "без username"
    await message.answer(
        f"Пользователь найден:\n"
        f"ID: {user['user_id']}\n"
        f"Имя: {user['full_name'] or 'Не указано'}\n"
        f"Username: {username_display}\n\n"
        f"Введите сумму для начисления:"
    )
    await state.set_state(AdminStates.waiting_for_amount)


@router.message(StateFilter(AdminStates.waiting_for_amount))
async def process_admin_amount(message: Message, state: FSMContext, bot: Bot):
    """Обработка суммы для начисления администратором"""
    try:
        amount = Decimal(message.text.replace(',', '.'))
        data = await state.get_data()
        user_id = data['admin_user_id']
        
        # Начисляем баланс
        await db.execute(
            "UPDATE users SET balance = balance + $1 WHERE user_id = $2",
            amount, user_id
        )
        
        # Создаем транзакцию
        await db.execute(
            """INSERT INTO transactions (user_id, transaction_type, amount, status, description, admin_id)
               VALUES ($1, 'admin_topup', $2, 'completed', 'Пополнение администратором', $3)""",
            user_id, amount, message.from_user.id
        )
        
        # Отправляем сообщение пользователю
        try:
            await bot.send_message(
                user_id,
                f"На ваш баланс зачислено {format_balance(amount)}!"
            )
        except Exception as e:
            # Если не удалось отправить сообщение (пользователь заблокировал бота и т.д.)
            pass
        
        await message.answer(
            f"✅ Баланс пользователя пополнен на {format_balance(amount)}"
        )
        await state.clear()
        
    except (ValueError, InvalidOperation):
        await message.answer("❌ Неверный формат суммы. Введите число, например: 100")


@router.callback_query(F.data == "admin_news")
async def admin_news_callback(callback: CallbackQuery, state: FSMContext):
    """Редактирование новостей"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    content = await db.fetchval(
        "SELECT setting_value FROM admin_settings WHERE setting_key = 'news_content'"
    )
    raw = (content or "").strip() or "— пусто —"
    # Экранируем для отображения в HTML-превью
    current = raw[:500].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if len(raw) > 500:
        current += "..."
    
    await callback.message.edit_text(
        f"📰 <b>Редактирование новостей</b>\n\n"
        f"<b>Текущий текст (что видят пользователи):</b>\n"
        f"<pre>{current}</pre>\n\n"
        f"Отправьте новое сообщение — оно полностью заменит текст новостей.\n",
        reply_markup=get_cancel_news_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_news)
    await callback.answer()


@router.message(StateFilter(AdminStates.waiting_for_news))
async def process_news_message(message: Message, state: FSMContext):
    """Сохранение нового текста новостей"""
    if not await is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        await state.clear()
        return
    
    new_content = message.text or message.caption or ""
    
    await db.execute(
        """INSERT INTO admin_settings (setting_key, setting_value) 
           VALUES ('news_content', $1)
           ON CONFLICT (setting_key) 
           DO UPDATE SET setting_value = $1, updated_at = CURRENT_TIMESTAMP""",
        new_content
    )
    
    await message.answer(
        "✅ Текст новостей обновлён. Пользователи видят новый контент при открытии раздела «Новости».",
        reply_markup=get_admin_back_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery):
    """Статистика системы"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    # Общая статистика
    total_users = await db.fetchval("SELECT COUNT(*) FROM users")
    total_deposits = await db.fetchval("SELECT COUNT(*) FROM deposits WHERE status = 'active'")
    total_balance = await db.fetchval("SELECT COALESCE(SUM(balance), 0) FROM users")
    total_deposits_amount = await db.fetchval(
        "SELECT COALESCE(SUM(current_balance), 0) FROM deposits WHERE status = 'active'"
    )
    
    stats_text = f"""
📊 <b>Статистика системы</b>

👥 Всего пользователей: {total_users}
💰 Общий баланс пользователей: {format_balance(total_balance)}
📈 Активных депозитов: {total_deposits}
💼 Сумма в депозитах: {format_balance(total_deposits_amount)}
"""
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=get_admin_back_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_admin")
async def back_to_admin_callback(callback: CallbackQuery, state: FSMContext):
    """Возврат в меню админки"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await state.clear()
    await callback.message.edit_text(
        LEXICON_RU['admin_panel'],
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_settings")
async def admin_settings_callback(callback: CallbackQuery):
    """Настройки админки"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⚙️ <b>Настройки админки</b>\n\nВыберите действие:",
        reply_markup=get_admin_settings_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_change_password")
async def admin_change_password_callback(callback: CallbackQuery, state: FSMContext):
    """Изменение пароля админки"""
    if not await is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🔑 Введите новый пароль для админки:",
        reply_markup=get_admin_back_keyboard()
    )
    await state.set_state(AdminStates.waiting_for_new_password)
    await callback.answer()


@router.message(StateFilter(AdminStates.waiting_for_new_password))
async def process_new_password(message: Message, state: FSMContext, bot: Bot):
    """Обработка нового пароля"""
    if not await is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        await state.clear()
        return
    
    new_password = message.text.strip()
    
    if len(new_password) < 3:
        await message.answer("❌ Пароль должен содержать минимум 3 символа")
        return
    
    # Сохраняем новый пароль в БД
    await db.execute(
        """INSERT INTO admin_settings (setting_key, setting_value) 
           VALUES ('admin_password', $1)
           ON CONFLICT (setting_key) 
           DO UPDATE SET setting_value = $1, updated_at = CURRENT_TIMESTAMP""",
        new_password
    )
    
    await bot.send_message(
        message.chat.id,
        "✅ Пароль успешно изменен!",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()
