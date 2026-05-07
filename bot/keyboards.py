
# Клавиатуры для основных действий пользователя. Включает различные типы кнопок: Reply, Inline, с изображениями.

from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from database.models import UserRole


def get_main_keyboard(role: UserRole = UserRole.USER) -> ReplyKeyboardMarkup:
    """
    Основная клавиатура бота. Изменяется в зависимости от роли пользователя.
    
    Args:
        role: Роль пользователя
        
    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопками
    """
    builder = ReplyKeyboardBuilder()
    
    # Общие кнопки для всех пользователей
    builder.row(
        KeyboardButton(text="📦 Каталог"),
        KeyboardButton(text="🔍 Поиск")
    )
    builder.row(
        KeyboardButton(text="❤️ Избранное"),
        KeyboardButton(text="🛒 Корзина")
    )
    builder.row(
        KeyboardButton(text="👤 Профиль"),
        KeyboardButton(text="⚙️ Настройки")
    )
    
    # Дополнительные кнопки для администраторов
    if role in [UserRole.ADMIN, UserRole.DEVELOPER]:
        builder.row(
            KeyboardButton(text="👑 Админ-панель"),
            KeyboardButton(text="📊 Отчеты")
        )
    
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def get_help_keyboard() -> InlineKeyboardMarkup:
    """
    Инлайн-клавиатура для команды /help.
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками
    """
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
    """
    Клавиатура для настроек бота
    
    Args:
        settings: Объект настроек пользователя
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с настройками
    """
    builder = InlineKeyboardBuilder()
    
    # Пункты настроек
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


def get_catalog_keyboard(session) -> InlineKeyboardMarkup:
    """
    Клавиатура каталога с категориями товаров.
    Категории соответствуют товарам из products.json.
    
    Args:
        session: Сессия базы данных (не используется в текущей версии)
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с категориями
    """
    builder = InlineKeyboardBuilder()
    
    # Категории, которые соответствуют товарам в products.json
    # Ключ - это категория для поиска в JSON-файле
    categories = [
        {"id": "корм", "name": "🍖 Корма"},
        {"id": "корм", "name": "🐱 Корма для кошек", "sub": "кошка"},
        {"id": "корм", "name": "🐶 Корма для собак", "sub": "собака"},
        {"id": "лекарства", "name": "💊 Лекарства и витамины"},
        {"id": "аксессуары", "name": "🏠 Аксессуары и амуниция"},
        {"id": "одежда", "name": "👕 Одежда для питомцев"},
        {"id": "игрушки", "name": "🧸 Игрушки"},
        {"id": "аксессуары", "name": "💧 Поилки и фонтанчики"},
    ]
    
    for cat in categories:
        # Формируем callback_data с указанием категории и подкатегории
        callback_data = f"catalog_{cat['id']}"
        if 'sub' in cat:
            callback_data += f"_{cat['sub']}"
        
        builder.row(
            InlineKeyboardButton(
                text=cat["name"],
                callback_data=callback_data
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
    """
    Клавиатура для корзины.
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="🗑 Очистить корзину",
            callback_data="cart_clear"
        ),
        InlineKeyboardButton(
            text="✅ Оформить заказ",
            callback_data="cart_checkout"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Продолжить покупки",
            callback_data="menu_main"
        )
    )
    
    return builder.as_markup()


def get_product_card_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для карточки товара.
    
    Args:
        product_id: ID товара для добавления в корзину
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками действий
    """
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="➕ В корзину",
            callback_data=f"add_to_cart_{product_id}"
        ),
        InlineKeyboardButton(
            text="❤️ В избранное",
            callback_data=f"add_to_favorites_{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад к поиску",
            callback_data="back_to_search"
        )
    )
def get_search_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для результатов поиска"""
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

    
    