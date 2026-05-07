
# Модели базы данных для Telegram-бота зоомагазина "Четыре Лапы".
# Всего 12 таблиц, удовлетворяющих требованиям к дипломному проекту.


from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, Boolean, DateTime, 
    Text, ForeignKey, Enum, JSON, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class UserRole(str, enum.Enum):
    """Роли пользователей для разграничения прав доступа"""
    DEVELOPER = "developer"    # Разработчик (полный доступ)
    ADMIN = "admin"            # Администратор (управление контентом)
    USER = "user"              # Обычный пользователь

class OrderStatus(str, enum.Enum):
    """Статусы заказов"""
    NEW = "new"                # Новый заказ
    PROCESSING = "processing"  # В обработке
    CONFIRMED = "confirmed"    # Подтвержден
    PAID = "paid"              # Оплачен
    SHIPPED = "shipped"        # Отправлен
    DELIVERED = "delivered"    # Доставлен
    CANCELLED = "cancelled"    # Отменен

class PaymentMethod(str, enum.Enum):
    """Способы оплаты"""
    CARD = "card"              # Банковская карта
    CASH = "cash"              # Наличные при получении
    ONLINE = "online"          # Онлайн-оплата

# 1. Таблица пользователей
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(64), nullable=True)
    first_name = Column(String(64), nullable=False)
    last_name = Column(String(64), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(128), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_activity = Column(DateTime(timezone=True), nullable=True)
    
    # Связи с другими таблицами
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")
    logs = relationship("UserLog", back_populates="user", cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, role={self.role})>"

# 2. Таблица категорий товаров
class Category(Base):
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    image_url = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    products = relationship("Product", back_populates="category")
    children = relationship("Category", backref="parent", remote_side=[id])
    
    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name})>"

# 3. Таблица товаров
class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    article = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    discount_price = Column(Float, nullable=True)
    stock_quantity = Column(Integer, default=0)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    brand = Column(String(128), nullable=True)
    pet_type = Column(String(32), nullable=True)  # собака, кошка, грызуны и т.д.
    weight = Column(String(32), nullable=True)    # вес/объем
    image_url = Column(String(512), nullable=True)
    additional_images = Column(JSON, nullable=True)  # список дополнительных изображений
    specifications = Column(JSON, nullable=True)     # характеристики в JSON
    is_available = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)     # рекомендуемый товар
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    favorites = relationship("Favorite", back_populates="product")
    reviews = relationship("Review", back_populates="product")
    
    def __repr__(self):
        return f"<Product(id={self.id}, article={self.article}, name={self.name})>"

# 4. Таблица заказов
class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_number = Column(String(32), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.NEW, nullable=False)
    total_amount = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0.0)
    delivery_address = Column(Text, nullable=True)
    delivery_city = Column(String(128), nullable=True)
    delivery_method = Column(String(64), nullable=True)
    payment_method = Column(Enum(PaymentMethod), nullable=True)
    customer_name = Column(String(128), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    customer_email = Column(String(128), nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Связи
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Order(id={self.id}, order_number={self.order_number}, status={self.status})>"

# 5. Таблица позиций заказа
class OrderItem(Base):
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Integer, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Связи
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    
    def __repr__(self):
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, quantity={self.quantity})>"

# 6. Таблица избранных товаров
class Favorite(Base):
    __tablename__ = "favorites"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Уникальный ключ для предотвращения дубликатов
    __table_args__ = (
        UniqueConstraint('user_id', 'product_id', name='uix_user_product'),
    )
    
    # Связи
    user = relationship("User", back_populates="favorites")
    product = relationship("Product", back_populates="favorites")
    
    def __repr__(self):
        return f"<Favorite(user_id={self.user_id}, product_id={self.product_id})>"

# 7. Таблица отзывов о товарах
class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)  # от 1 до 5
    text = Column(Text, nullable=True)
    is_approved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    user = relationship("User", backref="reviews")
    product = relationship("Product", back_populates="reviews")
    
    def __repr__(self):
        return f"<Review(id={self.id}, rating={self.rating}, product_id={self.product_id})>"

# 8. Таблица логов действий пользователей
class UserLog(Base):
    __tablename__ = "user_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    action = Column(String(64), nullable=False)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Индексы для быстрого поиска
    __table_args__ = (
        Index('ix_user_logs_user_id_action', 'user_id', 'action'),
        Index('ix_user_logs_created_at', 'created_at'),
    )
    
    # Связи
    user = relationship("User", back_populates="logs")
    
    def __repr__(self):
        return f"<UserLog(id={self.id}, user_id={self.user_id}, action={self.action})>"

# 9. Таблица настроек пользователей
class UserSettings(Base):
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    notifications_enabled = Column(Boolean, default=True)
    email_notifications = Column(Boolean, default=False)
    language = Column(String(8), default="ru")
    theme = Column(String(16), default="default")
    items_per_page = Column(Integer, default=10)
    auto_delete_messages = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    user = relationship("User", back_populates="settings")
    
    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id})>"

# 10. Таблица сессий пользователей
class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_token = Column(String(256), unique=True, nullable=False)
    fsm_state = Column(String(64), nullable=True)
    fsm_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Связи
    user = relationship("User", back_populates="sessions")
    
    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, token={self.session_token})>"

# 11. Таблица уведомлений
class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(256), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(32), default="info")  # info, warning, success, error
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Связи
    user = relationship("User", back_populates="notifications")
    
    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, title={self.title})>"

# 12. Таблица промокодов и акций
class Promotion(Base):
    __tablename__ = "promotions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(32), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    discount_percent = Column(Integer, nullable=True)
    discount_amount = Column(Float, nullable=True)
    min_order_amount = Column(Float, nullable=True)
    max_uses = Column(Integer, nullable=True)
    used_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    starts_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self):
        return f"<Promotion(id={self.id}, code={self.code})>"
    
# 13. Таблица корзины пользователя
class CartItem(Base):
    __tablename__ = "cart_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Уникальный ключ для предотвращения дубликатов
    __table_args__ = (
        UniqueConstraint('user_id', 'product_id', name='uix_user_cart_product'),
    )
    
    # Связи
    user = relationship("User", backref="cart_items")
    product = relationship("Product", backref="cart_items")