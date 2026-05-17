
# commands.py - Обработка основных команд бота с интеграцией товарной базы из products.json

import logging
from aiogram import Router, F, types, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandObject
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User, UserRole, UserLog
from bot.utils.decorators import require_auth, log_action
from ai_module.predict import get_ai_response
from bot.keyboards.main import (
    get_main_keyboard, 
    get_help_keyboard,
    get_catalog_keyboard,
    get_admin_keyboard,
    get_reports_keyboard,
    get_settings_keyboard
)

# Импорт товарной базы из JSON-файла
from product_db import ProductDB

router = Router()

#  КОРЗИНА (хранение в памяти) 
user_carts = {}


#  КОМАНДА /add (добавить в корзину) 
@router.message(F.command("add"))
@log_action("add_to_cart")
@require_auth
async def cmd_add_to_cart(message: Message, command: CommandObject):
    
    # Команда /add [ID товара или название] - Добавляет товар в корзину.
        
    query = command.args
    if not query:
        await message.answer(
            "❓ Укажите ID или название товара для добавления в корзину.\n"
            "Пример: <code>/add 1</code> или <code>/add корм для котят</code>\n\n"
            "Узнать ID товара можно через /search",
            parse_mode="HTML"
        )
        return
    
    user_id = message.from_user.id
    
    # Поиск товара в JSON-файле
    product_db = ProductDB('products.json')
    
    # Если ввели ID (число)
    if query.isdigit():
        product_id = int(query)
        products = [p for p in product_db.products if p.get('id') == product_id]
    else:
        # Поиск по названию, берём первый товар
        products = product_db.search_products(query, max_results=1)
    
    if not products:
        await message.answer(f"❌ Товар '<i>{query}</i>' не найден.", parse_mode="HTML")
        return
    
    product = products[0]
    
    # Инициализируем корзину пользователя, если её нет
    if user_id not in user_carts:
        user_carts[user_id] = []
    
    # Проверяем, есть ли уже такой товар в корзине
    found = False
    for item in user_carts[user_id]:
        if item['product'].get('id') == product.get('id'):
            item['quantity'] += 1
            found = True
            current_quantity = item['quantity']
            break
    
    if not found:
        user_carts[user_id].append({
            'product': product,
            'quantity': 1
        })
        current_quantity = 1
    
    await message.answer(
        f"✅ <b>Товар добавлен в корзину!</b>\n\n"
        f"📦 {product['name']}\n"
        f"💰 {product['price']} ₽\n"
        f"📦 Количество: {current_quantity}\n\n"
        f"🛒 Просмотр корзины: /cart\n"
        f"🗑 Очистить корзину: /clear_cart",
        parse_mode="HTML"
    )


# КОМАНДА /cart (показать корзину)
@router.message(F.command("cart"))
@log_action("cart")
@require_auth
async def cmd_cart(message: Message, session: AsyncSession):
    
    # Обработчик команды /cart.
    # Показывает содержимое корзины пользователя.
    
    user_id = message.from_user.id
    
    # Получаем корзину пользователя
    cart = user_carts.get(user_id, [])
    
    if not cart:
        await message.answer(
            "🛒 <b>Ваша корзина</b>\n\n"
            "Пока здесь пусто.\n\n"
            "🔍 <b>Как добавить товар:</b>\n"
            "• Найдите товар через /search\n"
            "• Запомните его ID (цифра в скобках)\n"
            "• Введите /add [ID]\n\n"
            "📝 <b>Пример:</b> /add 1\n\n"
            "💡 Или просто напишите /add и название товара",
            parse_mode="HTML"
        )
        return
    
    # Формируем ответ с корзиной
    total = 0
    response = "🛒 <b>Ваша корзина</b>\n\n"
    
    for i, item in enumerate(cart, 1):
        product = item['product']
        quantity = item['quantity']
        subtotal = product['price'] * quantity
        total += subtotal
        
        response += (
            f"{i}. <b>{product['name']}</b>\n"
            f"   💰 {product['price']} ₽ × {quantity} = {subtotal} ₽\n"
            f"   📦 ID товара: {product.get('id', '—')}\n\n"
        )
    
    response += f"<b>💰 Итого: {total} ₽</b>\n\n"
    response += "📦 <b>Для оформления заказа:</b> /checkout\n"
    response += "🗑 <b>Очистить корзину:</b> /clear_cart\n"
    response += "➕ <b>Добавить ещё:</b> /add [ID товара]"
    
    await message.answer(response, parse_mode="HTML")


#  КОМАНДА /clear_cart (очистить корзину) 
@router.message(F.command("clear_cart"))
@log_action("clear_cart")
@require_auth
async def cmd_clear_cart(message: Message):
    
    # Команда /clear_cart - Очищает корзину пользователя
    
    user_id = message.from_user.id
    
    if user_id in user_carts and user_carts[user_id]:
        user_carts[user_id] = []
        await message.answer("🗑 Корзина успешно очищена!")
    else:
        await message.answer("🛒 Корзина уже пуста.")


# КОМАНДА /checkout (оформление заказа) 
@router.message(F.command("checkout"))
@log_action("checkout")
@require_auth
async def cmd_checkout(message: Message):
    
    # Команда /checkout - Оформление заказа
    
    user_id = message.from_user.id
    cart = user_carts.get(user_id, [])
    
    if not cart:
        await message.answer(
            "🛒 Корзина пуста.\n\n"
            "Добавьте товары через команду /add",
            parse_mode="HTML"
        )
        return
    
    # Подсчёт итога
    total = sum(item['product']['price'] * item['quantity'] for item in cart)
    
    # Сохраняем заказ в лог (для диплома, так как нет интеграции с реальным интернет-магазином)
    from datetime import datetime
    order_preview = f"Заказ от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    for item in cart:
        order_preview += f"  - {item['product']['name']} x{item['quantity']} = {item['product']['price'] * item['quantity']} ₽\n"
    order_preview += f"Итого: {total} ₽"
    
    logging.info(f"Пользователь {user_id} оформил заказ:\n{order_preview}")
    
    # Очищаем корзину после оформления
    user_carts[user_id] = []
    
    await message.answer(
        f"✅ <b>Заказ оформлен!</b>\n\n"
        f"Спасибо за покупку в «4 Лапы»! 🐾\n\n"
        f"💰 Сумма заказа: <b>{total} ₽</b>\n\n"
        f"📞 <b>Что дальше?</b>\n"
        f"В ближайшее время с вами свяжется оператор для подтверждения заказа "
        f"и уточнения способа доставки и оплаты.\n\n"
        f"☎️ Контактный телефон: 8-800-XXX-XX-XX\n\n"
        f"🆔 Номер заказа для связи с оператором: #{user_id}{datetime.now().strftime('%d%m%y')}",
        parse_mode="HTML"
    )


#  КОМАНДА /start 
@router.message(F.command("start"))
@log_action("start")
async def cmd_start(message: Message, session: AsyncSession):
    
    # Обработчик команды /start
    # Регистрирует нового пользователя или приветствует существующего
    
    user_id = message.from_user.id
    
    # Проверяем, существует ли пользователь в базе
    result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        # Регистрация нового пользователя
        user = User(
            telegram_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            role=UserRole.USER
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        welcome_text = (
            f"🎉 Добро пожаловать, {message.from_user.first_name}!\n\n"
            f"Я бот-помощник зоомагазина 'Четыре Лапы'. Я помогу вам:\n"
            f"🔍 Найти нужные товары для ваших питомцев\n"
            f"💰 Узнать цены и наличие\n"
            f"📦 Оформить заказ\n"
            f"💡 Получить советы по уходу\n\n"
            f"Используйте кнопки ниже или команду /help для справки."
        )
    else:
        welcome_text = (
            f"👋 С возвращением, {user.first_name}!\n"
            f"Рад снова видеть вас в 'Четыре Лапы'!\n\n"
            f"Чем могу помочь сегодня?"
        )
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(user.role)
    )


# КОМАНДА /help 
@router.message(F.command("help"))
@log_action("help")
async def cmd_help(message: Message):
    
    # Обработчик команды /help.
    # Отображает справку по боту и выводит ФИО автора.
    
    help_text = (
        "📚 <b>Справка по боту 'Четыре Лапы'</b>\n\n"
        "<b>Поиск товаров:</b>\n"
        "/search [название] - Поиск товара\n"
        "/product [название] - Информация о товаре\n"
        "/price [название] - Узнать цену\n"
        "/stock [название] - Проверить наличие\n\n"
        "<b>Корзина и заказы:</b>\n"
        "/add [ID или название] - Добавить товар в корзину\n"
        "/cart - Просмотр корзины\n"
        "/clear_cart - Очистить корзину\n"
        "/checkout - Оформить заказ\n\n"
        "<b>Профиль и настройки:</b>\n"
        "/start - Начать работу\n"
        "/catalog - Каталог товаров\n"
        "/favorites - Избранное\n"
        "/profile - Мой профиль\n"
        "/settings - Настройки бота\n\n"
        "<b>Автор проекта:</b>\n"
        "Смирнова Ю.С.\n"
        "Студент группы о.ИЗДтв 23.1/Б3-23\n"
        "Дипломный проект 2026\n\n"
        "🔗 <b>Ссылка на бота:</b> @four_lapy_pets_bot"
    )
    
    await message.answer(
        help_text,
        reply_markup=get_help_keyboard(),
        parse_mode="HTML"
    )


#  КОМАНДА /catalog 
@router.message(F.command("catalog"))
@log_action("catalog")
@require_auth
async def cmd_catalog(message: Message, session: AsyncSession):
    
    # Обработчик команды /catalog.
    # Отображает каталог товаров с категориями.
    
    from bot.keyboards.main import get_catalog_keyboard
    
    await message.answer(
        "📦 <b>Каталог товаров 'Четыре Лапы'</b>\n\n"
        "Выберите категорию товаров:",
        reply_markup=await get_catalog_keyboard(session)
    )


# КОМАНДА /search 
@router.message(F.command("search"))
@log_action("search")
@require_auth
async def cmd_search(message: Message, command: CommandObject, session: AsyncSession):
    
    # Обработчик команды /search
    # Выполняет поиск товаров в products.json по ключевым словам
    
    query = command.args
    if not query:
        await message.answer(
            "❓ Пожалуйста, укажите что искать.\n"
            "Пример: <code>/search корм для собак</code>\n\n"
            "Или просто напишите свой вопрос в чат!"
        )
        return
    
    # Поиск товаров в JSON-файле
    product_db = ProductDB('products.json')
    products = product_db.search_products(query, max_results=10)
    
    if not products:
        # Используем ИИ для предложения альтернатив
        ai_response = get_ai_response(query)
        await message.answer(
            f"🔍 По запросу '<i>{query}</i>' ничего не найдено.\n\n"
            f"💡 {ai_response['response'] if 'response' in ai_response else ai_response}\n\n"
            f"Попробуйте изменить запрос или выберите категорию в каталоге."
        )
        return
    
    # Формирование ответа с результатами поиска
    response_text = f"🔍 <b>Результаты поиска по запросу:</b> '<i>{query}</i>'\n\n"
    
    for i, product in enumerate(products[:5], 1):
        availability = "✅ в наличии" if product.get('availability', False) else "❌ нет в наличии"
        
        response_text += (
            f"{i}. <b>{product['name']}</b>\n"
            f"   🆔 ID: {product.get('id', '—')}\n"
            f"   📦 Вес: {product.get('weight', '—')}\n"
            f"   🏷 Бренд: {product.get('brand', '—')}\n"
            f"   💰 Цена: {product['price']} ₽\n"
            f"   📦 {availability}\n"
            f"   ➕ Добавить в корзину: /add {product.get('id', '')}\n\n"
        )
    
    response_text += "🔎 Уточните запрос или используйте /add [ID] для добавления товара в корзину."
    
    await message.answer(response_text, parse_mode="HTML")


#  КОМАНДА /product 
@router.message(F.command("product"))
@log_action("product_info")
@require_auth
async def cmd_product(message: Message, command: CommandObject, session: AsyncSession):
    
    # Обработчик команды /product
    # Показывает подробную информацию о товаре
    
    query = command.args
    if not query:
        await message.answer(
            "❓ Пожалуйста, укажите название товара.\n"
            "Пример: <code>/product корм для котят</code>\n\n"
            "Или используйте /search для поиска."
        )
        return
    
    # Поиск товара в JSON-файле
    product_db = ProductDB('products.json')
    products = product_db.search_products(query, max_results=1)
    
    if not products:
        await message.answer(
            f"❌ Товар по запросу <code>{query}</code> не найден.\n\n"
            f"Проверьте правильность названия или воспользуйтесь поиском /search"
        )
        return
    
    product = products[0]
    
    # Формирование подробной информации о товаре
    availability = "✅ В наличии" if product.get('availability', False) else "❌ Нет в наличии"
    
    response_text = (
        f"📦 <b>{product['name']}</b>\n\n"
        f"🆔 ID: {product.get('id', '—')}\n"
        f"📦 Вес/Объем: {product.get('weight', 'Не указан')}\n"
        f"🏷 Бренд: {product.get('brand', 'Не указан')}\n"
        f"📂 Категория: {product.get('category', 'Не указана')}\n"
        f"💰 Цена: <b>{product['price']} ₽</b>\n"
        f"📦 Статус: {availability}\n\n"
        f"<b>Описание:</b>\n{product.get('description', 'Описание отсутствует')}\n\n"
        f"➕ <b>Добавить в корзину:</b> /add {product.get('id', '')}\n"
        f"🛒 <b>Перейти в корзину:</b> /cart"
    )
    
    await message.answer(response_text, parse_mode="HTML")


#  КОМАНДА /price 
@router.message(F.command("price"))
@log_action("price")
@require_auth
async def cmd_price(message: Message, command: CommandObject):
    
    # Обработчик команды /price.
    # Показывает цены на товары по запросу.
    
    query = command.args
    if not query:
        await message.answer(
            "❓ Пожалуйста, укажите название товара.\n"
            "Пример: <code>/price корм для котят</code>"
        )
        return
    
    # Поиск товаров в JSON-файле
    product_db = ProductDB('products.json')
    products = product_db.search_products(query, max_results=10)
    
    if not products:
        await message.answer(
            f"💰 По запросу '<i>{query}</i>' товары не найдены.\n"
            f"Попробуйте другой запрос или воспользуйтесь /search."
        )
        return
    
    response = "💰 <b>Цены на товары:</b>\n\n"
    for i, product in enumerate(products[:7], 1):
        response += f"{i}. <b>{product['name']}</b>\n"
        response += f"   💰 {product['price']} ₽\n"
        response += f"   🆔 ID: {product.get('id', '—')}\n"
        if product.get('weight'):
            response += f"   📦 {product['weight']}\n"
        response += "\n"
    
    response += "🔎 Для добавления в корзину: /add [ID]"
    
    await message.answer(response, parse_mode="HTML")


# КОМАНДА /stock 
@router.message(F.command("stock"))
@log_action("stock")
@require_auth
async def cmd_stock(message: Message, command: CommandObject):
    
    # Обработчик команды /stock.
    # Проверяет наличие товаров на складе.
    
    query = command.args
    if not query:
        await message.answer(
            "❓ Пожалуйста, укажите название товара.\n"
            "Пример: <code>/stock корм для котят</code>"
        )
        return
    
    # Поиск товаров в JSON-файле
    product_db = ProductDB('products.json')
    products = product_db.search_products(query, max_results=10)
    
    if not products:
        await message.answer(
            f"📦 По запросу '<i>{query}</i>' товары не найдены.\n"
            f"Попробуйте другой запрос или воспользуйтесь /search."
        )
        return
    
    response = "📦 <b>Наличие товаров:</b>\n\n"
    for i, product in enumerate(products[:7], 1):
        status_emoji = "✅" if product.get('availability', False) else "❌"
        status_text = "в наличии" if product.get('availability', False) else "нет в наличии"
        response += f"{i}. {status_emoji} <b>{product['name']}</b>\n"
        response += f"   📦 {status_text}\n"
        response += f"   🆔 ID: {product.get('id', '—')}\n"
        if product.get('price'):
            response += f"   💰 {product['price']} ₽\n"
        response += "\n"
    
    response += "🔎 Для добавления в корзину: /add [ID]"
    
    await message.answer(response, parse_mode="HTML")


#  КОМАНДА /favorites
@router.message(F.command("favorites"))
@log_action("favorites")
@require_auth
async def cmd_favorites(message: Message, session: AsyncSession):
    
    # Обработчик команды /favorites.
    # Показывает избранные товары пользователя.
    
    await message.answer(
        "❤️ <b>Избранные товары</b>\n\n"
        "Пока здесь пусто.\n\n"
        "Чтобы добавить товар в избранное, найдите его через /search, "
        "запомните ID и используйте команду:\n"
        "<code>/favorite_add 1</code>\n\n"
        "Эта функция будет доступна в следующих версиях бота.",
        parse_mode="HTML"
    )


#  КОМАНДА /profile
@router.message(F.command("profile"))
@log_action("profile")
@require_auth
async def cmd_profile(message: Message, session: AsyncSession):
    
    # Обработчик команды /profile.
    # Показывает информацию о профиле пользователя.
    
    user_id = message.from_user.id
    
    # Получаем данные пользователя из БД
    result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        await message.answer("❌ Профиль не найден. Используйте /start для регистрации.")
        return
    
    profile_text = (
        f"👤 <b>Мой профиль</b>\n\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"📛 Имя: {user.first_name or 'Не указано'}\n"
        f"🔖 Username: @{user.username or 'Не указан'}\n"
        f"📅 Зарегистрирован: {user.created_at.strftime('%d.%m.%Y') if user.created_at else 'Неизвестно'}\n"
        f"⭐️ Статус: {user.role.value if user.role else 'Пользователь'}\n\n"
        f"💡 <i>Для изменения данных обратитесь к администратору.</i>"
    )
    
    await message.answer(profile_text, parse_mode="HTML")


#  КОМАНДА /settings
@router.message(F.command("settings"))
@log_action("settings")
@require_auth
async def cmd_settings(message: Message, session: AsyncSession):
    
    # Обработчик команды /settings.
    # Отображает меню настроек бота.
    
    from bot.keyboards.main import get_settings_keyboard
    
    user_id = message.from_user.id
    result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one()
    
    # Получение или создание настроек пользователя
    from database.models import UserSettings
    
    settings_result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user.id)
    )
    settings = settings_result.scalar_one_or_none()
    
    if not settings:
        settings = UserSettings(user_id=user.id)
        session.add(settings)
        await session.commit()
        await session.refresh(settings)
    
    settings_text = (
        "⚙️ <b>Настройки бота</b>\n\n"
        f"🔔 Уведомления: {'✅ Вкл' if settings.notifications_enabled else '❌ Выкл'}\n"
        f"📧 Email-уведомления: {'✅ Вкл' if settings.email_notifications else '❌ Выкл'}\n"
        f"🌐 Язык: {settings.language}\n"
        f"🎨 Тема: {settings.theme}\n"
        f"📄 Товаров на странице: {settings.items_per_page}\n"
        f"🗑 Автоудаление сообщений: {'✅ Вкл' if settings.auto_delete_messages else '❌ Выкл'}\n\n"
        "Выберите пункт для изменения:"
    )
    
    await message.answer(
        settings_text,
        reply_markup=get_settings_keyboard(settings),
        parse_mode="HTML"
    )


#  ОБРАБОТЧИК СООБЩЕНИЙ 
@router.message(F.text)
@log_action("text_message")
@require_auth
async def handle_text_message(message: Message, session: AsyncSession):
    
    # Обработчик текстовых сообщений (не команд).
    # Анализирует запрос с помощью ИИ и отвечает пользователю.
    
    user_text = message.text.strip()
    user_id = message.from_user.id
    
    if not user_text:
        return
    
    # Отправляем индикатор "печатает..."
    await message.bot.send_chat_action(message.chat.id, action="typing")
    
    # Сначала пробуем найти товары в JSON-базе по ключевым словам
    product_db = ProductDB('products.json')
    products = product_db.search_products(user_text, max_results=5)
    
    if products and len(products) > 0:
        # Если нашли товары, показываем их с ID для добавления в корзину
        response = "🔍 <b>Нашёл для вас:</b>\n\n"
        for i, p in enumerate(products[:5], 1):
            status = "✅" if p.get('availability', False) else "❌"
            response += (
                f"{i}. <b>{p['name']}</b>\n"
                f"   🆔 ID: {p.get('id', '—')}\n"
                f"   💰 {p['price']} ₽ {status}\n"
                f"   ➕ /add {p.get('id', '')}\n\n"
            )
        response += "💡 Введите <b>/add [ID]</b> чтобы добавить товар в корзину"
        await message.answer(response, parse_mode="HTML")
        return
    
    # Если товары не найдены, используем ИИ для ответа
    try:
        ai_response = get_ai_response(user_text)
        response = ai_response.get('response', ai_response) if isinstance(ai_response, dict) else ai_response
        
        # Добавляем подсказку для пользователя
        if "не найдено" in response or "ничего не найдено" in response:
            response += "\n\n💡 Попробуйте использовать команду /search для поиска товаров."
        
        await message.answer(response, parse_mode="HTML")
    except Exception as e:
        # Если ИИ недоступен, даём стандартный ответ
        fallback_text = (
            "🐾 Я ещё учусь отвечать на такие вопросы.\n\n"
            "Попробуйте:\n"
            "• Использовать команду /search для поиска товаров\n"
            "• Уточнить ваш запрос\n"
            "• Написать по-другому\n\n"
            "Или свяжитесь с оператором по телефону 8-800-XXX-XX-XX"
        )
        await message.answer(fallback_text)
#  ПРОСТЫЕ ОБРАБОТЧИКИ ПРИВЕТСТВИЙ И ПРОЩАНИЙ (без ИИ)

# Список приветственных фраз
GREETING_WORDS = [
    "привет", "здравствуй", "здравствуйте", "добрый день", 
    "доброе утро", "добрый вечер", "хай", "хелло", "hello", 
    "приветствую", "салют", "здарова", "здаров", "ку", "йоу",
    "доброго времени суток", "рад встрече", "рада встрече"
]

# Список прощальных фраз
GOODBYE_WORDS = [
    "пока", "до свидания", "прощай", "прощайте", "увидимся",
    "до встречи", "до скорого", "всего доброго", "всего хорошего",
    "счастливо", "бай", "bye", "goodbye", "гудбай", "чао",
    "до связи", "спокойной ночи", "доброй ночи", "удачи",
    "завершить", "выход", "стоп", "хватит"
]

# Список фраз для вызова администратора
ADMIN_WORDS = [
    "админ", "администратор", "оператор", "человек", "живой человек",
    "позови админа", "позвать админа", "связь с оператором",
    "нужен человек", "хочу поговорить с человеком", "консультант",
    "живой консультант", "поддержка", "служба поддержки"
]

# Список фраз благодарности
THANKS_WORDS = [
    "спасибо", "благодарю", "спс", "thx", "thanks", "thank you",
    "от души", "благодарствую", "выручил", "помог"
]


@router.message(F.text.lower().in_(GREETING_WORDS))
async def greeting_handler(message: Message):
    """
    Обработчик приветственных фраз.
    Отвечает дружелюбно и показывает, что умеет бот.
    """
    user_name = message.from_user.first_name or "друг"
    
    # Разные варианты приветствий для разнообразия
    import random
    greetings = [
        f"👋 Здравствуйте, {user_name}! Рады видеть вас в зоомагазине «Четыре Лапы»! Чем могу помочь?",
        f"🐾 Привет, {user_name}! Мяу-гав! Я ваш помощник по товарам для животных. Что ищете?",
        f"😊 Добрый день, {user_name}! Как ваш питомец? Я здесь, чтобы помочь с выбором!",
        f"🌟 Здравствуйте! Я бот-консультант «Четыре Лапы». Подсказать что-нибудь?",
    ]
    
    await message.answer(
        random.choice(greetings) + "\n\n"
        "Я могу помочь:\n"
        "🔍 Найти товар — просто напишите, что ищете\n"
        "📋 Показать каталог — /catalog\n"
        "🛒 Работать с корзиной — /cart\n"
        "❓ Рассказать о командах — /help"
    )


@router.message(F.text.lower().in_(GOODBYE_WORDS))
async def goodbye_handler(message: Message):
    """
    Обработчик прощальных фраз.
    Прощается и предлагает вернуться.
    """
    user_name = message.from_user.first_name or "друг"
    
    import random
    goodbyes = [
        f"👋 До свидания, {user_name}! Будем рады видеть вас снова! Хорошего дня!",
        f"🐾 Пока, {user_name}! Мяу-гав! Заходите ещё за вкусняшками для питомца!",
        f"😊 Всего доброго, {user_name}! Если понадобится помощь — я всегда здесь!",
        f"🌟 До встречи, {user_name}! Пусть ваш питомец будет счастлив и здоров!",
    ]
    
    await message.answer(random.choice(goodbyes))


@router.message(F.text.lower().in_(ADMIN_WORDS))
async def admin_handler(message: Message):
    """
    Обработчик запросов на связь с администратором.
    """
    await message.answer(
        "📞 <b>Нужна помощь человека?</b>\n\n"
        "Вы можете связаться с оператором:\n"
        "📧 Email: support@4lapy.ru\n"
        "📱 Телефон: 8-800-XXX-XX-XX\n\n"
        "🕐 Время работы: с 9:00 до 21:00\n\n"
        "Или просто напишите ваш вопрос здесь, и я постараюсь помочь!",
        parse_mode="HTML"
    )


@router.message(F.text.lower().in_(THANKS_WORDS))
async def thanks_handler(message: Message):
    """
    Обработчик благодарностей.
    """
    import random
    replies = [
        "😊 Всегда пожалуйста! Рада помочь!",
        "🐾 На здоровье! Пушистого вам настроения!",
        "🌟 Обращайтесь ещё! Я всегда на связи!",
        "💚 Приятно помогать! Хорошего дня вам и вашему питомцу!",
    ]
    
    await message.answer(random.choice(replies))


@router.message(F.text.lower().in_(["что ты умеешь", "что ты можешь", "твои возможности", "команды"]))
async def capabilities_handler(message: Message):
    
    # Обработчик вопроса о возможностях бота
    
    await message.answer(
        "🐾 <b>Вот что я умею:</b>\n\n"
        "🔍 <b>Поиск товаров</b> — просто напишите, что ищете\n"
        "📋 <b>Каталог</b> — /catalog\n"
        "💰 <b>Узнать цену</b> — /price [название]\n"
        "📦 <b>Проверить наличие</b> — /stock [название]\n"
        "🛒 <b>Корзина</b> — /cart\n"
        "➕ <b>Добавить в корзину</b> — /add [ID]\n"
        "✅ <b>Оформить заказ</b> — /checkout\n"
        "📞 <b>Позвать админа</b> — напишите «администратор»\n\n"
        "<b>Подробнее:</b> /help",
        parse_mode="HTML"
    )


@router.message(F.text.lower().in_(["как дела", "как ты", "как жизнь", "как настроение"]))
async def how_are_you_handler(message: Message):
    
    # Обработчик вопроса «как дела».
    
    import random
    replies = [
        "😊 У меня всё отлично! Я всегда готов помогать с выбором товаров для питомцев!",
        "🐾 Прекрасно! Особенно когда нахожу для вас лучшие товары!",
        "🤖 Я бот, поэтому всегда в форме! Что ищете сегодня?",
        "💚 Замечательно! Особенно когда помогаю заботиться о любимых питомцах!",
    ]
    
    await message.answer(random.choice(replies))


@router.message(F.text.lower().in_(["бот", "ты бот", "ты робот", "ты живой", "ты настоящий"]))
async def bot_identity_handler(message: Message):
    
    # Обработчик вопроса о том, бот ли это.
    
    await message.answer(
        "🤖 Да, я бот-помощник зоомагазина «Четыре Лапы»!\n\n"
        "Но я создан, чтобы помогать вам с выбором товаров для ваших любимых питомцев 🐾\n\n"
        "Если нужен живой человек — напишите «администратор»!"
    )

#  ОБРАБОТЧИКИ КНОПОК ОСНОВНОЙ КЛАВИАТУРЫ

@router.message(F.text == "📦 Каталог")
async def button_catalog(message: Message, session: AsyncSession):
    """Обработчик кнопки «Каталог»."""
    await message.answer(
        "📦 <b>Каталог товаров 'Четыре Лапы'</b>\n\n"
        "Выберите категорию товаров:",
        reply_markup=get_catalog_keyboard(session),
        parse_mode="HTML"
    )


@router.message(F.text == "🔍 Поиск")
async def button_search(message: Message):
    """Обработчик кнопки «Поиск»."""
    await message.answer(
        "🔍 <b>Поиск товаров</b>\n\n"
        "Просто напишите, что вы ищете, и я найду это в каталоге!\n\n"
        "Например: <i>корм для собак, игрушка для кошек, ошейник</i>",
        parse_mode="HTML"
    )


@router.message(F.text == "🛒 Корзина")
async def button_cart(message: Message):
    """Обработчик кнопки «Корзина»."""
    user_id = message.from_user.id
    cart = user_carts.get(user_id, [])

    if not cart:
        await message.answer(
            "🛒 <b>Ваша корзина</b>\n\n"
            "Пока здесь пусто.\n\n"
            "🔍 Найдите товары через поиск и добавьте их в корзину!",
            parse_mode="HTML"
        )
        return

    total = 0
    response = "🛒 <b>Ваша корзина</b>\n\n"
    for i, item in enumerate(cart, 1):
        product = item['product']
        quantity = item['quantity']
        subtotal = product['price'] * quantity
        total += subtotal
        response += (
            f"{i}. <b>{product['name']}</b>\n"
            f"   💰 {product['price']} ₽ × {quantity} = {subtotal} ₽\n"
            f"   🆔 ID: {product.get('id', '—')}\n\n"
        )
    response += f"<b>💰 Итого: {total} ₽</b>\n\n"
    response += "✅ Оформить заказ: /checkout\n"
    response += "🗑 Очистить корзину: /clear_cart"

    await message.answer(response, parse_mode="HTML")


@router.message(F.text == "👤 Профиль")
async def button_profile(message: Message, session: AsyncSession):
    """Обработчик кнопки «Профиль»."""
    user_id = message.from_user.id
    result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("❌ Профиль не найден. Используйте /start для регистрации.")
        return

    profile_text = (
        f"👤 <b>Мой профиль</b>\n\n"
        f"🆔 ID: <code>{user.telegram_id}</code>\n"
        f"📛 Имя: {user.first_name or 'Не указано'}\n"
        f"🔖 Username: @{user.username or 'Не указан'}\n"
        f"📅 Зарегистрирован: {user.created_at.strftime('%d.%m.%Y') if user.created_at else 'Неизвестно'}\n"
        f"⭐️ Статус: {user.role.value if user.role else 'Пользователь'}"
    )

    await message.answer(profile_text, parse_mode="HTML")


@router.message(F.text == "❤️ Избранное")
async def button_favorites(message: Message):
    """Обработчик кнопки «Избранное»."""
    await message.answer(
        "❤️ <b>Избранные товары</b>\n\n"
        "Здесь будут храниться ваши любимые товары.\n"
        "Чтобы добавить товар в избранное, найдите его через поиск!",
        parse_mode="HTML"
    )


@router.message(F.text == "🎁 Акции")
async def button_promotions(message: Message):
    """Обработчик кнопки «Акции»."""
    await message.answer(
        "🎁 <b>Акции и скидки</b>\n\n"
        "🔥 Сейчас действуют специальные предложения:\n"
        "• Скидка 15% на все корма для кошек\n"
        "• При покупке 2 игрушек — третья в подарок\n"
        "• Бесплатная доставка при заказе от 3000 ₽\n\n"
        "Уточняйте подробности в каталоге!",
        parse_mode="HTML"
    )


@router.message(F.text == "❓ Помощь")
async def button_help(message: Message):
    """Обработчик кнопки «Помощь»."""
    help_text = (
        "📚 <b>Справка по боту 'Четыре Лапы'</b>\n\n"
        "<b>Поиск товаров:</b>\n"
        "• Напишите, что ищете — я найду!\n"
        "• Команда /search [название]\n\n"
        "<b>Корзина и заказы:</b>\n"
        "• Кнопка 🛒 Корзина — посмотреть заказ\n"
        "• /add [ID] — добавить товар\n"
        "• /checkout — оформить заказ\n\n"
        "<b>Автор проекта:</b>\n"
        "Смирнова Ю.С.\n"
        "Студент группы о.ИЗДтв 23.1/Б3-23\n"
        "Дипломный проект 2026"
    )

    await message.answer(help_text, reply_markup=get_help_keyboard(), parse_mode="HTML")


@router.message(F.text == "⚙️ Настройки")
async def button_settings(message: Message, session: AsyncSession):
    """Обработчик кнопки «Настройки»."""
    user_id = message.from_user.id
    result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one()

    from database.models import UserSettings
    settings_result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user.id)
    )
    settings = settings_result.scalar_one_or_none()

    if not settings:
        settings = UserSettings(user_id=user.id)
        session.add(settings)
        await session.commit()
        await session.refresh(settings)

    settings_text = (
        "⚙️ <b>Настройки бота</b>\n\n"
        f"🔔 Уведомления: {'✅ Вкл' if settings.notifications_enabled else '❌ Выкл'}\n"
        f"📧 Email-уведомления: {'✅ Вкл' if settings.email_notifications else '❌ Выкл'}\n"
        f"🌐 Язык: {settings.language}\n"
        f"🎨 Тема: {settings.theme}\n"
        f"📄 Товаров на странице: {settings.items_per_page}\n"
        f"🗑 Автоудаление: {'✅ Вкл' if settings.auto_delete_messages else '❌ Выкл'}\n\n"
        "Выберите пункт для изменения:"
    )

    await message.answer(settings_text, reply_markup=get_settings_keyboard(settings), parse_mode="HTML")


@router.message(F.text == "ℹ️ О магазине")
async def button_about(message: Message):
    """Обработчик кнопки «О магазине»."""
    await message.answer(
        "ℹ️ <b>О магазине «Четыре Лапы»</b>\n\n"
        "🐾 Мы — крупнейшая сеть зоомагазинов в России!\n\n"
        "📦 Более 10 000 товаров для ваших питомцев\n"
        "🚚 Быстрая доставка по всей стране\n"
        "💳 Удобные способы оплаты\n"
        "⭐️ Гарантия качества от проверенных брендов\n\n"
        "Работаем с любовью к животным с 2005 года!",
        parse_mode="HTML"
    )


@router.message(F.text == "📞 Связь с нами")
async def button_contact(message: Message):
    """Обработчик кнопки «Связь с нами»."""
    await message.answer(
        "📞 <b>Связь с нами</b>\n\n"
        "📱 Телефон горячей линии: 8-800-XXX-XX-XX\n"
        "📧 Email: support@4lapy.ru\n"
        "🕐 Время работы: ежедневно с 9:00 до 21:00\n\n"
        "💬 Или просто напишите ваш вопрос здесь!\n"
        "Если нужен живой оператор — напишите «администратор».",
        parse_mode="HTML"
    )


@router.message(F.text == "📝 Отзывы")
async def button_reviews(message: Message):
    """Обработчик кнопки «Отзывы»."""
    await message.answer(
        "📝 <b>Отзывы</b>\n\n"
        "Мы ценим ваше мнение! Напишите свой отзыв о нашем магазине прямо в чат, "
        "и мы обязательно его учтём.\n\n"
        "⭐️ Также вы можете оценить товары после покупки!",
        parse_mode="HTML"
    )


@router.message(F.text == "🏠 Главная")
async def button_home(message: Message, session: AsyncSession):
    """Обработчик кнопки «Главная» — возвращает основную клавиатуру."""
    user_id = message.from_user.id
    result = await session.execute(
        select(User).where(User.telegram_id == user_id)
    )
    user = result.scalar_one_or_none()
    role = user.role if user else UserRole.USER

    await message.answer(
        "🏠 Вы на главной. Выберите действие:",
        reply_markup=get_main_keyboard(role)
    )


@router.message(F.text == "👑 Админ")
async def button_admin(message: Message):
    """Обработчик кнопки «Админ» (только для админов)."""
    await message.answer(
        "👑 <b>Панель администратора</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )


def register_commands_handlers(dp: Dispatcher):
    """
    Регистрирует все обработчики команд из этого файла в диспетчере
    Вызывается из handlers/__init__.py
    """
    dp.include_router(router)
