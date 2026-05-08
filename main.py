
# main.py - Вход в приложение Telegram-бота для зоомагазина "Четыре Лапы". С помощью запускаем бота, инициализируем базу данных и все компоненты.

import asyncio
import logging
import os
import sys
from pathlib import Path

# Добавляем корневую директорию в путь для импортов
sys.path.append(str(Path(__file__).parent))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, BotCommandScopeDefault
from dotenv import load_dotenv

from database.engine import init_db, close_db
from bot.middlewares import register_all_middlewares
from bot.utils.logger import setup_logger
from bot.utils.scheduler import setup_scheduler
from product_db import ProductDB
from handlers import register_all_handlers


# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logger = setup_logger("main")

# Конфигурация бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("Токен бота не найден! Установите переменную окружения BOT_TOKEN")
    sys.exit(1)

# Инициализация хранилища состояний

REDIS_URL = os.getenv("REDIS_URL")
if REDIS_URL:
    storage = RedisStorage.from_url(REDIS_URL)
    logger.info("Используется Redis для хранения состояний FSM")
else:
    storage = MemoryStorage()
    logger.warning("Используется MemoryStorage (не рекомендуется для продакшена)")

# Инициализация бота и диспетчера
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=storage)

# Загружаем товарную базу
product_db = ProductDB('products.json')
logger.info(f"Товарная база загружена: {len(product_db.products)} товаров")

async def set_bot_commands():
    
    # Установим команды бота, которые отображаются в меню Telegram.Всего 12 команд, из них 5 с параметрами.
   
    commands = [
        BotCommand(command="start", description="🚀 Начать работу с ботом"),
        BotCommand(command="help", description="❓ Получить справку (ФИО автора)"),
        BotCommand(command="catalog", description="📦 Показать каталог товаров"),
        BotCommand(command="search", description="🔍 Поиск товара [название]"),
        BotCommand(command="product", description="📋 Информация о товаре [артикул]"),
        BotCommand(command="price", description="💰 Проверить цену [артикул]"),
        BotCommand(command="stock", description="📊 Проверить наличие [артикул]"),
        BotCommand(command="cart", description="🛒 Просмотр корзины"),
        BotCommand(command="favorites", description="❤️ Избранные товары"),
        BotCommand(command="settings", description="⚙️ Настройки бота"),
        BotCommand(command="profile", description="👤 Мой профиль"),
        BotCommand(command="report", description="📈 Отчет (для админов)"),
    ]
    
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    logger.info("Команды бота установлены")

async def on_startup():
    # Запускаем бота
    logger.info("Запуск бота...")
    
    # Проведем инициализацию базы данных
    await init_db()
    
    # Установим команды
    await set_bot_commands()
    
    # Зарегистрируем  все обработчики
    register_all_handlers(dp)
    
    # Регистрация middleware
    register_all_middlewares(dp)
    
    # Настроим планировщика задач
    setup_scheduler()
    
    # Загрузим ИИ-модели 
    try:
        from ai_module.predict import AIModelManager
        manager = AIModelManager()
        manager.load_model()
        logger.info("ИИ-модель загружена успешно")
    except Exception as e:
        logger.warning(f"Не удалось загрузить ИИ-модель: {e}")
    
    logger.info("Бот успешно запущен!")

async def on_shutdown():
    """
    Действия при остановке бота.
    """
    logger.info("Остановка бота...")
    
    # Закрытие соединения с базой данных
    await close_db()
    
    # Закрытие сессии бота
    await bot.session.close()
    
    logger.info("Бот остановлен")

async def main():
    """
    Основная функция запуска бота.
    """
    # Регистрация функций запуска и остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Запуск поллинга
    try:
        logger.info("Запуск поллинга...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await on_shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Необработанное исключение: {e}")
        sys.exit(1)
