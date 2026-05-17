# main.py - Вход в приложение Telegram-бота для зоомагазина "Четыре Лапы". С помощью запускаем бота, инициализируем базу данных и все компоненты.
import asyncio
import logging
import os
import sys
import threading
from pathlib import Path
from bot.db_provider import set_product_db

# Добавляем корневую директорию в путь для импортов
sys.path.append(str(Path(__file__).parent))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault
from dotenv import load_dotenv
from flask import Flask

from database.engine import init_db, close_db
from bot.middlewares import register_all_middlewares
from bot.utils.logger import setup_logger
from bot.utils.scheduler import setup_scheduler
from bot.handlers import register_all_handlers
from product_db import ProductDB

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logger = setup_logger("main")

# Конфигурация бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("Токен бота не найден! Установите переменную окружения BOT_TOKEN")
    sys.exit(1)

# Используем MemoryStorage (без Redis)
storage = MemoryStorage()
logger.info("Используется MemoryStorage для хранения состояний")
    
# Инициализация бота и диспетчера
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=storage)

# Загружаем товарную базу из JSON
product_db = ProductDB('products.json')
logger.info(f"Товарная база загружена: {len(product_db.products)} товаров")

set_product_db(product_db)

# ВЕБ-СЕРВЕР ДЛЯ RENDER 
web_app = Flask(__name__)

@web_app.route('/')
def health_check():
    return "Bot is running!", 200

@web_app.route('/health')
def health():
    return "OK", 200

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    web_app.run(host='0.0.0.0', port=port)

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

# ЗАПУСК И ОСТАНОВКА
async def on_startup():
    logger.info("Запуск бота...")
    
    # Проведем инициализацию базы данных
    await init_db()
    
    # Установим команд
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
    except ImportError:  # ← отдельно ловит ImportError
        logger.info("ИИ-модуль не установлен, пропускаем")
    except Exception as e:  # ← остальные исключения
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

# ГЛАВНАЯ ФУНКЦИЯ
async def main():
    # Регистрация функций запуска и остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Запуск веб-сервера в фоновом потоке (нужно для Render)
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()
    logger.info("Веб-сервер для Render запущен в фоновом потоке на порту " + os.environ.get('PORT', '10000'))
        
    # Запуск поллинга (основной поток, здесь бот будет принимать сообщения)
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
