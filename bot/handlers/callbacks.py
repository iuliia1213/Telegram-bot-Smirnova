# Обработчики callback-запросов (нажатия на inline-кнопки)

import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import Dispatcher

from product_db import ProductDB
from bot.handlers.commands import user_carts

router = Router()

# Инициализация базы товаров
product_db = ProductDB('products.json')


@router.callback_query(F.data.startswith("catalog_"))
async def process_catalog_callback(callback: CallbackQuery):
    # Обработчик нажатий на категории каталога.
    # Получаем категорию из callback_data
    
    data_parts = callback.data.replace("catalog_", "")
    
    await callback.answer(f"Загружаю категорию...")
    
    # Поиск товаров по категории
    if "_" in data_parts:
        # Составная категория: корм_кошка, корм_собака
        parts = data_parts.split("_")
        main_category = parts[0]  # корм
        sub_category = parts[1] if len(parts) > 1 else None  # кошка
        
        # Фильтруем товары
        filtered_products = []
        for product in product_db.products:
            product_category = product.get('category', '').lower()
            product_name = product.get('name', '').lower()
            product_pet = product.get('pet_type', '').lower()
            
            # Проверяем основную категорию
            if main_category in product_category or main_category in product_name:
                # Если есть подкатегория — фильтруем по типу животного
                if sub_category:
                    if sub_category in product_pet or sub_category in product_name:
                        filtered_products.append(product)
                else:
                    filtered_products.append(product)
    else:
        # Простая категория: игрушки, лекарства, аксессуары
        category = data_parts
        filtered_products = product_db.search_products(category, max_results=10)
    
    # Формируем ответ
    if not filtered_products:
        await callback.message.edit_text(
            f"📦 <b>Категория пуста</b>\n\n"
            f"В этой категории пока нет товаров.\n"
            f"Попробуйте другую категорию или воспользуйтесь поиском.",
            parse_mode="HTML"
        )
        return
    
    # Показываем товары
    response = f"📦 <b>Товары в категории:</b>\n\n"
    
    for i, product in enumerate(filtered_products[:10], 1):
        availability = "✅" if product.get('availability', False) else "❌"
        response += (
            f"{i}. <b>{product['name']}</b>\n"
            f"   💰 {product['price']} ₽ {availability}\n"
            f"   🆔 ID: {product.get('id', '—')}\n"
            f"   ➕ /add {product.get('id', '')}\n\n"
        )
    
    response += "💡 Нажмите /add [ID] чтобы добавить товар в корзину"
    
    await callback.message.edit_text(response, parse_mode="HTML")


@router.callback_query(F.data == "menu_main")
async def process_back_to_main(callback: CallbackQuery):
    """Обработчик кнопки «На главную»."""
    await callback.answer("Возвращаю на главную...")
    await callback.message.edit_text(
        "🏠 Вы на главной. Используйте кнопки внизу для навигации.",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "help_docs")
async def process_help_docs(callback: CallbackQuery):
    # Обработчик кнопки «Документация»
    await callback.answer("Документация")
    await callback.message.answer(
        "📖 <b>Документация</b>\n\n"
        "Полная документация по боту доступна в проекте.\n"
        "Основные команды смотрите в /help",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "help_support")
async def process_help_support(callback: CallbackQuery):
    """Обработчик кнопки «Поддержка»."""
    await callback.answer("Поддержка")
    await callback.message.answer(
        "💬 <b>Поддержка</b>\n\n"
        "Свяжитесь с нами:\n"
        "📧 Email: support@4lapy.ru\n"
        "📱 Телефон: 8-800-XXX-XX-XX",
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("add_to_cart_"))
async def process_add_to_cart(callback: CallbackQuery):
    # Обработчик добавления товара в корзину через кнопку
    product_id = callback.data.replace("add_to_cart_", "")
    user_id = callback.from_user.id
    
    # Ищем товар по ID
    product = None
    for p in product_db.products:
        if str(p.get('id')) == str(product_id):
            product = p
            break
    
    if not product:
        await callback.answer("Товар не найден!", show_alert=True)
        return
    
    if user_id not in user_carts:
        user_carts[user_id] = []
    
    found = False
    for item in user_carts[user_id]:
        if item['product'].get('id') == product.get('id'):
            item['quantity'] += 1
            found = True
            break
    
    if not found:
        user_carts[user_id].append({
            'product': product,
            'quantity': 1
        })
    
    cart_count = sum(item['quantity'] for item in user_carts[user_id])
    await callback.answer(
        f"✅ {product['name']} добавлен в корзину! (всего товаров: {cart_count})", 
        show_alert=True
    )

    
@router.callback_query(F.data == "cart_clear")
async def process_cart_clear(callback: CallbackQuery):
    """Обработчик очистки корзины."""
    user_id = callback.from_user.id  # ← ДОБАВИТЬ
    if user_id in user_carts:
        user_carts[user_id] = []
    await callback.answer("Корзина очищена!", show_alert=True)


@router.callback_query(F.data == "cart_checkout")
async def process_cart_checkout(callback: CallbackQuery):
    # Обработчик оформления заказа
    await callback.answer("Перехожу к оформлению...")
    await callback.message.answer(
        "Для оформления заказа используйте команду /checkout"
    )

def register_callbacks_handlers(dp: Dispatcher):
    # Регистрирует все обработчики callback-запросов в диспетчере.
    dp.include_router(router)
