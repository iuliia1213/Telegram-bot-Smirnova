
# Декораторы для проверки прав доступа и логирования действий.
# Обеспечивают 3 уровня доступа: разработчик, администратор, пользователь.


from functools import wraps
from typing import List, Optional
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import User, UserRole, UserLog

def require_role(allowed_roles: List[UserRole]):
    
    # Декоратор для проверки роли пользователя
    """
    Args:
        allowed_roles: Список разрешенных ролей
        
    Returns:
        decorator: Функция-декоратор
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(event, *args, **kwargs):
            # Определяем тип события (Message или CallbackQuery)
            if isinstance(event, Message):
                user_id = event.from_user.id
                message = event
            elif isinstance(event, CallbackQuery):
                user_id = event.from_user.id
                message = event.message
            else:
                return await func(event, *args, **kwargs)
            
            # Получаем сессию из kwargs или создаем новую
            session = kwargs.get('session')
            if not session:
                from database.engine import AsyncSessionLocal
                async with AsyncSessionLocal() as session:
                    result = await session.execute(
                        select(User).where(User.telegram_id == user_id)
                    )
                    user = result.scalar_one_or_none()
                    
                    if not user or user.role not in allowed_roles:
                        await message.answer(
                            "⛔ У вас недостаточно прав для выполнения этой команды.\n"
                            f"Требуемая роль: {', '.join([r.value for r in allowed_roles])}"
                        )
                        return
                    
                    kwargs['session'] = session
                    return await func(event, *args, **kwargs)
            else:
                result = await session.execute(
                    select(User).where(User.telegram_id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user or user.role not in allowed_roles:
                    await message.answer(
                        "⛔ У вас недостаточно прав для выполнения этой команды."
                    )
                    return
                
                return await func(event, *args, **kwargs)
        
        return wrapper
    return decorator

def require_auth(func):
    
    # Декоратор для проверки аутентификации пользователя.
    # Автоматически регистрирует нового пользователя.
    
    @wraps(func)
    async def wrapper(message: Message, *args, **kwargs):
        session = kwargs.get('session')
        
        if not session:
            from database.engine import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id == message.from_user.id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    # Автоматическая регистрация
                    user = User(
                        telegram_id=message.from_user.id,
                        username=message.from_user.username,
                        first_name=message.from_user.first_name,
                        last_name=message.from_user.last_name,
                        role=UserRole.USER
                    )
                    session.add(user)
                    await session.commit()
                
                kwargs['session'] = session
                return await func(message, *args, **kwargs)
        else:
            return await func(message, *args, **kwargs)
    
    return wrapper

def log_action(action_name: str):
    """
    Декоратор для логирования действий пользователя.
    
    Args:
        action_name: Название действия для логирования
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(message: Message, *args, **kwargs):
            # Выполняем основную функцию
            result = await func(message, *args, **kwargs)
            
            # Логируем действие
            try:
                session = kwargs.get('session')
                if session:
                    user_result = await session.execute(
                        select(User).where(User.telegram_id == message.from_user.id)
                    )
                    user = user_result.scalar_one_or_none()
                    
                    if user:
                        log_entry = UserLog(
                            user_id=user.id,
                            action=action_name,
                            details={"message": message.text}
                        )
                        session.add(log_entry)
                        await session.commit()
            except Exception as e:
                import logging
                logging.getLogger("petstore_bot").error(f"Ошибка логирования: {e}")
            
            return result
        
        return wrapper
    return decorator