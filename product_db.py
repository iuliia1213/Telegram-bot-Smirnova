import json
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional

# Настройка логгера
logger = logging.getLogger(__name__)

class ProductDB:
    def __init__(self, file_path: str = "products.json"):
        self.file_path = file_path
        self.products = []
        self._load_products()
    
    def _load_products(self):
        # Загружает товары из JSON-файла
        # Пробуем разные пути к файлу
        paths_to_try = [
            self.file_path,  
            Path(__file__).parent / self.file_path,  
            Path.cwd() / self.file_path,  # рабочая директория
            Path(__file__).parent.parent / self.file_path,  # на уровень выше
        ]
        
        loaded = False
        for path in paths_to_try:
            if os.path.exists(str(path)):
                try:
                    with open(str(path), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Поддержка разных структур JSON
                        if isinstance(data, dict) and 'products' in data:
                            self.products = data['products']
                        elif isinstance(data, list):
                            self.products = data
                        else:
                            self.products = []
                        loaded = True
                        logger.info(f"✅ Загружено {len(self.products)} товаров из {path}")
                        break
                except Exception as e:
                    logger.error(f"❌ Ошибка загрузки {path}: {e}")
                    continue
        
        if not loaded:
            logger.error(f"❌ Файл {self.file_path} не найден ни в одном из путей")
            self.products = []
            
    #  Поиск товаров по текстовому запросу
    def search_products(self, query: str, max_results: int = 5) -> List[Dict]:
        if not self.products:
            logger.warning("Поиск: список товаров пуст")
            return []
        
        query_lower = query.lower()
        results = []
        
        for product in self.products:
            # Ищем совпадения в названии и категории
            name = product.get('name', '').lower()
            category = product.get('category', '').lower()
            brand = product.get('brand', '').lower()
            
            # Полное совпадение или частичное
            if (query_lower in name or 
                query_lower in category or 
                query_lower in brand):
                results.append(product)
                continue
            # Проверяем отдельные ключевые слова
            keywords = query_lower.split()
            for keyword in keywords:
                if len(keyword) > 2 and (keyword in name or keyword in category or keyword in brand):
                    if product not in results:
                        results.append(product)
                    break
        
        return results[:max_results]
        
    def get_product_by_id(self, product_id) -> Optional[Dict]:
        # Поиск товара по ID
        if not self.products:
            return None
        
        str_id = str(product_id)
        for product in self.products:
            if str(product.get('id', '')) == str_id:
                return product
        return None
    
    def get_product_by_article(self, article: str) -> Optional[Dict]:
        # Поиск товара по артикулу
        if not self.products:
            return None
        
        # Убираем префикс P если есть
        clean_article = str(article).replace('P', '').replace('p', '')
        for product in self.products:
            # Проверяем по id
            if str(product.get('id', '')) == clean_article:
                return product
            # Проверяем по article (если есть в JSON)
            if str(product.get('article', '')) == str(article):
                return product
        return None
    
    def get_products_by_category(self, category: str) -> List[Dict]:
        # Товары по категории
        if not self.products:
            return []
        
        cat_lower = category.lower()
        return [p for p in self.products 
                if p.get('category', '').lower() == cat_lower]
    
    def get_categories(self) -> List[str]:
        # Получить все категории
        if not self.products:
            return []
        
        categories = set()
        for product in self.products:
            cat = product.get('category', 'other')
            categories.add(cat)
        return sorted(list(categories)) 
        
     # Форматирует список товаров в читаемый ответ
    def format_product_response(self, products: List[Dict]) -> str:
        if not products:
            return "🔍 К сожалению, по вашему запросу ничего не найдено.\n\nПопробуйте:\n• изменить формулировку\n• спросить про другую категорию товаров"
        
        response = "🐾 **Вот что мне удалось найти:**\n\n"
        for i, product in enumerate(products, 1):
            name = product.get('name', 'Без названия')
            weight = product.get('weight', '—')
            price = product.get('price', 0)
            availability = product.get('availability', False)
            status = "✅ в наличии" if availability else "❌ нет в наличии"
            
            # Обрезаем длинное название
            if len(name) > 50:
                name = name[:47] + "..."
            
            response += f"{i}. **{name}**\n"
            response += f"   📦 Вес: {weight}\n"
            response += f"   💰 Цена: {price:,} руб.\n".replace(',', ' ')
            response += f"   📦 {status}\n"
            
            description = product.get('description', '')
            if description:
                if len(description) > 100:
                    description = description[:97] + "..."
                response += f"   📝 {description}\n"
            
            response += f"   🔍 `/product {product.get('id')}`\n\n"
        
        return response

    def format_single_product(self, product: Dict) -> str:
        # Форматирует один товар (полная информация)
        name = product.get('name', 'Без названия')
        weight = product.get('weight', '—')
        price = product.get('price', 0)
        brand = product.get('brand', '—')
        category = product.get('category', '—')
        target = product.get('target', '—')
        availability = product.get('availability', False)
        description = product.get('description', 'Описание отсутствует')
        
        status = "✅ В наличии" if availability else "❌ Нет в наличии"
        
        response = f"""
🐱 *{name}*

📋 *Характеристики:*
• Категория: {category}
• Бренд: {brand}
• Для кого: {target}
• Вес/объем: {weight}

💰 *Цена:* {price:,} руб.

📊 *Статус:* {status}

📝 *Описание:*
{description}

🔍 Для заказа используйте корзину: `/cart add {product.get('id')}`
"""
        return response.replace(',', ' ')
    
    def get_all_products(self, limit: int = None) -> List[Dict]:
        # Возвращает все товары
        if limit:
            return self.products[:limit]
        return self.products
    
    def get_random_products(self, count: int = 5) -> List[Dict]:
        # Возвращает случайные товары
        import random
        if not self.products:
            return []
        if len(self.products) <= count:
            return self.products.copy()
        return random.sample(self.products, count)
    
    def __len__(self) -> int:
        return len(self.products)
