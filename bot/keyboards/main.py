# Клавиатуры для основных действий пользователя.Включает различные типы кнопок: Reply, Inline, с изображениями

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from database.models import UserRole


def get_main_keyboard(role: UserRole = UserRole.USER) -> ReplyKeyboardMarkup:
    """
    Основная клавиатура бота — 12 кнопок в 3 ряда по 4 штуки.
    Пользователю не нужно писать команды — всё доступно по кнопкам.
    """
    builder = ReplyKeyboardBuilder()
    
    # Ряд 1: Каталог, Поиск, Корзина, Профиль
    builder.row(
        KeyboardButton(text="📦 Каталог"),
        KeyboardButton(text="🔍 Поиск"),
        KeyboardButton(text="🛒 Корзина"),
        KeyboardButton(text="👤 Профиль")
    )
    
    # Ряд 2: Избранное, Акции, Помощь, Настройки
    builder.row(
        KeyboardButton(text="❤️ Избранное"),
        KeyboardButton(text="🎁 Акции"),
        KeyboardButton(text="❓ Помощь"),
        KeyboardButton(text="⚙️ Настройки")
    )
    
    # Ряд 3: Инфо, Связь, Отзывы, Админ (если есть права)
    builder.row(
        KeyboardButton(text="ℹ️ О магазине"),
        KeyboardButton(text="📞 Связь с нами"),
        KeyboardButton(text="📝 Отзывы"),
        KeyboardButton(text="👑 Админ") if role in [UserRole.ADMIN, UserRole.DEVELOPER] 
        else KeyboardButton(text="🏠 Главная")
    )
    
    return builder.as_markup(resize_keyboard=True)


def get_help_keyboard() -> InlineKeyboardMarkup:
    # Инлайн-клавиатура для команды /help.
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="📖 Документация",
            callback_data="help_docs"
        ),
        InlineKeyboardButton(
            text="💬 Поддержка",
            callback_data="help_support"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🏠 На главную",
            callback_data="menu_main"
        )
    )
    
    return builder.as_markup()


def get_settings_keyboard(settings) -> InlineKeyboardMarkup:
    # Клавиатура для настроек бота.
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text=f"🔔 Уведомления: {'✅' if settings.notifications_enabled else '❌'}",
            callback_data="settings_notifications"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"📧 Email: {'✅' if settings.email_notifications else '❌'}",
            callback_data="settings_email"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"🌐 Язык: {settings.language.upper()}",
            callback_data="settings_language"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"🎨 Тема: {settings.theme}",
            callback_data="settings_theme"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"📄 Товаров на странице: {settings.items_per_page}",
            callback_data="settings_items_per_page"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"🗑 Автоудаление: {'✅' if settings.auto_delete_messages else '❌'}",
            callback_data="settings_auto_delete"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="menu_main"
        )
    )
    
    return builder.as_markup()


def get_catalog_keyboard(session=None) -> InlineKeyboardMarkup:
    # Клавиатура каталога с категориями товаров.
    builder = InlineKeyboardBuilder()
    
    categories = [
        {"id": "корм_кошка", "name": "🐱 Корма для кошек"},
        {"id": "корм_собака", "name": "🐶 Корма для собак"},
        {"id": "лекарства", "name": "💊 Лекарства и витамины"},
        {"id": "аксессуары", "name": "🏠 Аксессуары"},
        {"id": "одежда", "name": "👕 Одежда для питомцев"},
        {"id": "игрушки", "name": "🧸 Игрушки"},
        {"id": "поилки", "name": "💧 Поилки и фонтанчики"},
    ]
    
    for cat in categories:
        builder.row(
            InlineKeyboardButton(
                text=cat["name"],
                callback_data=f"catalog_{cat['id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="🔍 Поиск по каталогу",
            switch_inline_query_current_chat=""
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 На главную",
            callback_data="menu_main"
        )
    )
    
    return builder.as_markup()


def get_cart_keyboard() -> InlineKeyboardMarkup:
    # Клавиатура для корзины.
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="cart_clear"),
        InlineKeyboardButton(text="✅ Оформить заказ", callback_data="cart_checkout")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Продолжить покупки", callback_data="menu_main")
    )
    
    return builder.as_markup()


def get_product_card_keyboard(product_id: int) -> InlineKeyboardMarkup:
    # Клавиатура для карточки товара.
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="➕ В корзину", callback_data=f"add_to_cart_{product_id}"),
        InlineKeyboardButton(text="❤️ В избранное", callback_data=f"add_to_favorites_{product_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад к поиску", callback_data="back_to_search")
    )
    
    return builder.as_markup()


def get_search_keyboard() -> InlineKeyboardMarkup:
    # Клавиатура для результатов поиска.
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛒 Добавить в корзину", callback_data="add_to_cart"),
        InlineKeyboardButton(text="❤️ В избранное", callback_data="add_to_favorites")
    )
    builder.row(
        InlineKeyboardButton(text="🔍 Новый поиск", callback_data="new_search"),
        InlineKeyboardButton(text="🔙 На главную", callback_data="menu_main")
    )
    return builder.as_markup()


def get_admin_keyboard() -> InlineKeyboardMarkup:
    # Клавиатура для админ-панели.
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"))
    builder.row(InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"))
    builder.row(InlineKeyboardButton(text="📈 Отчеты", callback_data="admin_reports"))
    builder.row(InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"))
    builder.row(InlineKeyboardButton(text="🔙 На главную", callback_data="menu_main"))
    
    return builder.as_markup()


def get_reports_keyboard() -> InlineKeyboardMarkup:
    # Клавиатура для отчетов
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text="📊 Активность пользователей", callback_data="report_activity"))
    builder.row(InlineKeyboardButton(text="💰 Продажи", callback_data="report_sales"))
    builder.row(InlineKeyboardButton(text="📦 Популярные товары", callback_data="report_products"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_reports_back"))
    
    return builder.as_markup()
