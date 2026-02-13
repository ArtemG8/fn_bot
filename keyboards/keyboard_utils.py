from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="👤 Профиль"))
    builder.add(KeyboardButton(text="💰 Баланс"))
    builder.add(KeyboardButton(text="📈 Депозиты"))
    builder.add(KeyboardButton(text="💳 Пополнить"))
    builder.add(KeyboardButton(text="💸 Вывести"))
    builder.add(KeyboardButton(text="👥 Реферальная программа"))
    builder.add(KeyboardButton(text="📰 Новости"))
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup(resize_keyboard=True)


def get_deposit_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для работы с депозитами"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="➕ Открыть депозит", callback_data="create_deposit"))
    builder.add(InlineKeyboardButton(text="📊 Мои депозиты", callback_data="list_deposits"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    builder.adjust(1)
    return builder.as_markup()


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура администратора"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="📋 Ожидающие транзакции", callback_data="admin_pending"))
    builder.add(InlineKeyboardButton(text="➕ Начислить баланс", callback_data="admin_add_balance"))
    builder.add(InlineKeyboardButton(text="📰 Новости", callback_data="admin_news"))
    builder.add(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))
    builder.add(InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings"))
    builder.add(InlineKeyboardButton(text="🚪 Выйти из админки", callback_data="exit_admin"))
    builder.adjust(1)
    return builder.as_markup()


def get_transaction_keyboard(transaction_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения/отклонения транзакции"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="✅ Одобрить",
        callback_data=f"approve_{transaction_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="❌ Отклонить",
        callback_data=f"reject_{transaction_id}"
    ))
    builder.adjust(2)
    return builder.as_markup()


def get_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка назад"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    return builder.as_markup()


def get_admin_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка назад для админки"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin"))
    return builder.as_markup()


def get_admin_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек админки"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔑 Изменить пароль", callback_data="admin_change_password"))
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin"))
    builder.adjust(1)
    return builder.as_markup()


def get_cancel_reject_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для отмены ввода причины отклонения"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_reject"))
    return builder.as_markup()


def get_cancel_news_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для отмены редактирования новостей"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_admin"))
    return builder.as_markup()


# Рефералы: записей на страницу и максимальная длина callback_data (64 байта)
REFERRALS_PER_PAGE = 10


def get_referral_keyboard(referrals_count: int) -> InlineKeyboardMarkup:
    """Клавиатура реферальной программы: кнопка «Список рефералов» если есть рефералы"""
    builder = InlineKeyboardBuilder()
    if referrals_count > 0:
        builder.add(InlineKeyboardButton(
            text=f"📋 Список рефералов ({referrals_count})",
            callback_data="referrals_page_0"
        ))
    return builder.as_markup()


def get_referrals_list_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура пагинации списка рефералов"""
    builder = InlineKeyboardBuilder()
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="◀ Назад", callback_data=f"referrals_page_{page - 1}"))
    row.append(InlineKeyboardButton(text="🔙 К программе", callback_data="referral_back"))
    if page < total_pages - 1:
        row.append(InlineKeyboardButton(text="Вперёд ▶", callback_data=f"referrals_page_{page + 1}"))
    for btn in row:
        builder.add(btn)
    return builder.as_markup()
