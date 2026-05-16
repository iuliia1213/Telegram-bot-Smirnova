# Модуль для подключения к базе данных PostgreSQL и SQLite

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv

load_dotenv()

# Проверяем, есть ли готовая строка подключения (Render)
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Render: используем предоставленную строку подключения PostgreSQL
    # Заменяем postgresql:// на postgresql+asyncpg:// для асинхронной работы
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    print(f"Используется PostgreSQL (Render)")
    
    # Для PostgreSQL - с параметрами пула
    engine = create_async_engine(
        DATABASE_URL,
        echo=os.getenv("DB_ECHO", "False").lower() == "true",
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True
    )
else:
    # Локально: используем SQLite
    SQLITE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot_database.db")
    DATABASE_URL = f"sqlite+aiosqlite:///{SQLITE_PATH}"
    print(f"Используется SQLite (локально): {SQLITE_PATH}")
    
    # Для SQLite - БЕЗ параметров пула
    engine = create_async_engine(
        DATABASE_URL,
        echo=os.getenv("DB_ECHO", "False").lower() == "true"
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
