# Модуль для генерации отчетов
import csv
import os
from datetime import datetime
from aiogram.types import FSInputFile


async def generate_activity_report(session) -> str:
    """
    Генерация отчета об активности пользователей
    
    Args:
        session: Сессия базы данных
        
    Returns:
        str: Путь к созданному файлу отчета
    """
    from sqlalchemy import select
    from database.models import UserLog, User
    
    # Получаем данные об активности
    result = await session.execute(
        select(UserLog)
        .order_by(UserLog.created_at.desc())
        .limit(1000)
    )
    logs = result.scalars().all()
    
    # Создаем директорию для отчетов
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    # Формируем имя файла
    filename = f"activity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(reports_dir, filename)
    
    # Записываем CSV
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Дата', 'Пользователь', 'Действие', 'Детали'])
        
        for log in logs:
            user_info = f"{log.user.first_name if log.user else 'Unknown'}"
            writer.writerow([
                log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                user_info,
                log.action,
                str(log.details) if log.details else ''
            ])
    
    return filepath


async def generate_sales_report(session) -> str:
    """
    Генерация отчета о продажах.
    
    Args:
        session: Сессия базы данных
        
    Returns:
        str: Путь к созданному файлу отчета
    """
    from sqlalchemy import select, func
    from database.models import Order
    
    # Получаем статистику по заказам
    total_orders = await session.scalar(select(func.count(Order.id)))
    completed_orders = await session.scalar(
        select(func.count(Order.id)).where(Order.status == 'delivered')
    )
    total_revenue = await session.scalar(
        select(func.sum(Order.total_amount)).where(Order.status == 'delivered')
    ) or 0
    
    # Создаем директорию для отчетов
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    # Формируем имя файла
    filename = f"sales_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(reports_dir, filename)
    
    # Записываем отчет
    with open(filepath, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Показатель', 'Значение'])
        writer.writerow(['Всего заказов', total_orders or 0])
        writer.writerow(['Выполнено заказов', completed_orders or 0])
        writer.writerow(['Общая выручка (₽)', f"{total_revenue:.2f}"])
        writer.writerow(['Дата генерации', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
    
    return filepath
