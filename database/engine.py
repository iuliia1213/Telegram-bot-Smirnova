
# Модуль для подключения к базе данных PostgreSQL с использованием SQLAlchemy и asyncpg.


import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

load_dotenv()

# Настройки подключения к PostgreSQL
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "petstore_bot")

# Формирование URL для подключения
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Создание асинхронного движка
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "False").lower() == "true",  # Логирование SQL запросов
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True  # Проверка соединения перед использованием
)

# Создание фабрики сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

async def get_db() -> AsyncSession:
    """
    Генератор для получения сессии базы данных.
    Используется в качестве зависимости в хендлерах.
    
    Yields:
        AsyncSession: Асинхронная сессия для работы с БД
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """
    Инициализация базы данных: создание всех таблиц.
    Вызывается при запуске приложения.
    """
    from database.models import Base
    
    async with engine.begin() as conn:
        # Создание всех таблиц
        await conn.run_sync(Base.metadata.create_all)
        print("База данных инициализирована, таблицы созданы")

async def close_db():
    """
    Закрытие соединения с базой данных.
    Вызывается при завершении работы приложения.
    """
    await engine.dispose()
    print("Соединение с базой данных закрыто")