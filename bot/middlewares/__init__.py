import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware, Dispatcher
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseMiddleware):
    # Middleware для логирования всех сообщений
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Логируем входящие сообщения
        if hasattr(event, 'text') and event.text:
            logger.info(f"Получено сообщение: {event.text}")
        return await handler(event, data)

def register_all_middlewares(dp: Dispatcher):
    # Регистрирует все middleware для диспетчера
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    logger.info("Middleware зарегистрированы")
