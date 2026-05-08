# Обработчики для администраторов и разработчиков.
# Включает команды для управления ботом и просмотра отчетов.

from aiogram import Router, F, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandObject
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database.models import User, UserRole, UserLog, Order, Product
from bot.utils.decorators import require_role
from bot.keyboards.admin import get_admin_keyboard, get_reports_keyboard
from bot.utils.reports import generate_activity_report, generate_sales_report

router = Router()

@router.message(Command("admin"))
@require_role([UserRole.ADMIN, UserRole.DEVELOPER])
async def cmd_admin_panel(message: Message):
    
    # Панель администратора.
    # Доступна только для пользователей с ролью ADMIN или DEVELOPER.
    
    await message.answer(
        "👑 <b>Панель администратора</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard()
    )

@router.message(Command("report"))
@require_role([UserRole.ADMIN, UserRole.DEVELOPER])
async def cmd_report_menu(message: Message):
    
    # Меню отчетов для администратора.
    # Предоставляет доступ к различным отчетам.
    
    await message.answer(
        "📊 <b>Отчеты и статистика</b>\n\n"
        "Выберите тип отчета:",
        reply_markup=get_reports_keyboard()
    )

@router.callback_query(F.data == "report_activity")
@require_role([UserRole.ADMIN, UserRole.DEVELOPER])
async def process_activity_report(callback: CallbackQuery, session: AsyncSession):
    
    # Генерация и отправка отчета об активности пользователей.
    # Использует файловую систему для сохранения отчета.
    
    import os
    import csv
    from datetime import datetime
    from aiogram.types import FSInputFile
    
    await callback.answer("Генерация отчета...")
    
    # Получение данных об активности
    result = await session.execute(
        select(UserLog)
        .order_by(UserLog.created_at.desc())
        .limit(1000)
    )
    logs = result.scalars().all()
    
    # Создание CSV файла с отчетом
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    
    filename = f"activity_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(reports_dir, filename)
    
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
    
    # Отправка файла пользователю
    file = FSInputFile(filepath)
    await callback.message.answer_document(
        file,
        caption=f"📊 Отчет об активности пользователей\n"
                f"Сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
                f"Всего записей: {len(logs)}"
    )
    
    await callback.message.edit_reply_markup(reply_markup=None)

@router.callback_query(F.data == "report_sales")
@require_role([UserRole.ADMIN, UserRole.DEVELOPER])
async def process_sales_report(callback: CallbackQuery, session: AsyncSession):
    """
    Генерация отчета о продажах.
    """
    await callback.answer("Генерация отчета о продажах...")
    
    # Получение статистики по заказам
    total_orders = await session.scalar(select(func.count(Order.id)))
    completed_orders = await session.scalar(
        select(func.count(Order.id)).where(Order.status == 'delivered')
    )
    total_revenue = await session.scalar(
        select(func.sum(Order.total_amount)).where(Order.status == 'delivered')
    ) or 0
    
    # Статистика по товарам
    from database.models import OrderItem
    top_products = await session.execute(
        select(Product.name, func.sum(OrderItem.quantity).label('total_sold'))
        .join(OrderItem, OrderItem.product_id == Product.id)
        .group_by(Product.id)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(10)
    )
    
    report_text = (
        "💰 <b>Отчет о продажах</b>\n\n"
        f"Всего заказов: {total_orders}\n"
        f"Выполнено заказов: {completed_orders}\n"
        f"Общая выручка: {total_revenue:.2f} ₽\n\n"
        "<b>Топ-10 товаров по продажам:</b>\n"
    )
    
    for i, (name, sold) in enumerate(top_products, 1):
        report_text += f"{i}. {name}: {sold} шт.\n"
    
    await callback.message.answer(report_text)
    await callback.message.edit_reply_markup(reply_markup=None)

@router.message(Command("broadcast"))
@require_role([UserRole.ADMIN, UserRole.DEVELOPER])
async def cmd_broadcast(message: Message, command: CommandObject):
    
    # Команда для рассылки сообщений всем пользователям.
     
    from bot.utils.broadcast import start_broadcast
    
    text = command.args
    if not text:
        await message.answer(
            "❓ Укажите текст для рассылки.\n"
            "Пример: <code>/broadcast Важное объявление!</code>"
        )
        return
    
    await message.answer(f"📢 Начинаю рассылку сообщения...")
    
    # Запуск рассылки (реализация в utils/broadcast.py)
    result = await start_broadcast(text, message.bot)
    
    await message.answer(
        f"✅ Рассылка завершена!\n"
        f"Отправлено: {result['sent']}\n"
        f"Ошибок: {result['failed']}"
    )
def register_admin_handlers(dp: Dispatcher):
    """
    Регистрирует все обработчики администратора из этого файла в диспетчере
    Вызывается из handlers/__init__.py
    """
    dp.include_router(router)
