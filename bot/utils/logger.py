
# Модуль для настройки логирования действий пользователей и системных событий


import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime

def setup_logger(name: str = "petstore_bot") -> logging.Logger:
    """
    Настройка логгера с ротацией файлов и выводом в консоль.
    
    Args:
        name: Имя логгера
        
    Returns:
        logger: Настроенный логгер
    """
    # Создание директории для логов
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Создание логгера
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Форматтер для логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Обработчик для файла с ротацией
    file_handler = RotatingFileHandler(
        log_dir / f"{name}.log",
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Добавление обработчиков
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

class UserActionLogger:
    
    # Класс для логирования действий пользователей в базу данных.
    
    
    @staticmethod
    async def log_action(session, user_id: int, action: str, details: dict = None):
        """
        Запись действия пользователя в базу данных.
        
        Args:
            session: Сессия базы данных
            user_id: ID пользователя
            action: Название действия
            details: Дополнительные детали в виде словаря
        """
        from database.models import UserLog
        
        log_entry = UserLog(
            user_id=user_id,
            action=action,
            details=details
        )
        session.add(log_entry)
        await session.commit()