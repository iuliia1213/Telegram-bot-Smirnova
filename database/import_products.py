# Скрипт для импорта товаров из products.json в PostgreSQL

import asyncio
import json
import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.append(str(Path(__file__).parent.parent))

from database.engine import AsyncSessionLocal
from database.models import Product, Category
from sqlalchemy import select


async def import_products():
    
    # Импорт товаров из products.json в базу данных PostgreSQL
    
    print("=" * 60)
    print("Импорт товаров из products.json в PostgreSQL")
    print("=" * 60)
    
    # Читаем JSON-файл
    json_path = Path(__file__).parent.parent / "products.json"
    
    if not json_path.exists():
        print(f"❌ Файл {json_path} не найден!")
        return
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        products_data = data.get('products', [])
    
    print(f"📦 Найдено товаров в JSON: {len(products_data)}")
    
    async with AsyncSessionLocal() as session:
        #  Создаём категории 
        categories_map = {}
        
        for product_data in products_data:
            cat_name = product_data.get('category', 'other')
            if cat_name not in categories_map:
                # Проверяем, существует ли категория в БД
                result = await session.execute(
                    select(Category).where(Category.name == cat_name)
                )
                category = result.scalar_one_or_none()
                
                if not category:
                    category = Category(
                        name=cat_name,
                        description=f"Товары категории '{cat_name}'",
                        is_active=True
                    )
                    session.add(category)
                    await session.flush()
                    print(f"✅ Создана категория: {cat_name}")
                else:
                    print(f"📁 Категория уже существует: {cat_name}")
                
                categories_map[cat_name] = category.id
        
        await session.commit()
        
        #  Импортируем товары 
        imported_count = 0
        updated_count = 0
        error_count = 0
        
        for product_data in products_data:
            try:
                # Формируем артикул (используем ID из JSON или генерируем)
                product_id = product_data.get('id')
                article = f"P{product_id:06d}" if product_id else product_data.get('article', '')
                name = product_data.get('name', '')
                
                if not name:
                    print(f"⚠️ Пропущен товар без названия: {product_data}")
                    error_count += 1
                    continue
                
                # Проверяем, существует ли товар по артикулу
                result = await session.execute(
                    select(Product).where(Product.article == article)
                )
                existing = result.scalar_one_or_none()
                
                category_id = categories_map.get(product_data.get('category', 'other'))
                price = product_data.get('price', 0)
                availability = product_data.get('availability', False)
                
                if existing:
                    # Обновляем существующий товар
                    existing.name = name
                    existing.description = product_data.get('description', '')
                    existing.price = price
                    existing.discount_price = product_data.get('discount_price')
                    existing.stock_quantity = 1 if availability else 0
                    existing.category_id = category_id
                    existing.brand = product_data.get('brand', '')
                    existing.pet_type = product_data.get('target', product_data.get('pet_type'))
                    existing.weight = product_data.get('weight', '')
                    existing.is_available = availability
                    existing.specifications = {
                        'weight': product_data.get('weight'),
                        'brand': product_data.get('brand'),
                        'subcategory': product_data.get('subcategory'),
                        'target': product_data.get('target')
                    }
                    updated_count += 1
                    print(f"🔄 Обновлён товар: {name[:50]}...")
                else:
                    # Создаём новый товар
                    product = Product(
                        article=article,
                        name=name,
                        description=product_data.get('description', ''),
                        price=price,
                        discount_price=product_data.get('discount_price'),
                        stock_quantity=1 if availability else 0,
                        category_id=category_id,
                        brand=product_data.get('brand', ''),
                        pet_type=product_data.get('target', product_data.get('pet_type')),
                        weight=product_data.get('weight', ''),
                        is_available=availability,
                        is_featured=False,
                        specifications={
                            'weight': product_data.get('weight'),
                            'brand': product_data.get('brand'),
                            'subcategory': product_data.get('subcategory'),
                            'target': product_data.get('target')
                        }
                    )
                    session.add(product)
                    imported_count += 1
                    print(f"➕ Добавлен товар: {name[:50]}...")
                
                await session.flush()
                
            except Exception as e:
                print(f"❌ Ошибка при импорте товара {product_data.get('name', 'unknown')}: {e}")
                error_count += 1
        
        await session.commit()
    
    # Вывод итогов 
    print("\n" + "=" * 60)
    print("📊 ИТОГИ ИМПОРТА:")
    print(f"   ✅ Добавлено новых товаров: {imported_count}")
    print(f"   🔄 Обновлено существующих товаров: {updated_count}")
    print(f"   ❌ Ошибок: {error_count}")
    print(f"   📦 Всего товаров в JSON: {len(products_data)}")
    
    # Проверка количества товаров в БД
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Product))
        total_in_db = len(result.scalars().all())
        print(f"   🗄️ Всего товаров в БД после импорта: {total_in_db}")
    
    print("=" * 60)


async def clear_products():
    
    # Очистка таблицы товаров (для переимпорта).
    
    print("=" * 60)
    print("Очистка таблицы товаров...")
    print("=" * 60)
    
    async with AsyncSessionLocal() as session:
        # Удаляем все товары
        await session.execute(Product.__table__.delete())
        await session.commit()
        
        print("✅ Таблица товаров очищена")


async def main():
    
    # Основная функция выбора действия.
    
    print("\n" + "=" * 60)
    print("ИМПОРТ ТОВАРОВ В POSTGRESQL")
    print("=" * 60)
    print("1. Импортировать товары (существующие будут обновлены)")
    print("2. Очистить таблицу товаров")
    print("3. Очистить и импортировать заново")
    print("=" * 60)
    
    choice = input("Выберите действие (1-3): ").strip()
    
    if choice == "1":
        await import_products()
    elif choice == "2":
        await clear_products()
    elif choice == "3":
        await clear_products()
        await import_products()
    else:
        print("❌ Неверный выбор")


if __name__ == "__main__":
    asyncio.run(main())