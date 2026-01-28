from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Date
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from datetime import datetime

Base = declarative_base()

DATABASE_URL = "sqlite:///./totli_holva.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================
# TOVAR KIRIMI (PURCHASE)
# ==========================================

class Purchase(Base):
    """Tovar kirim hujjati"""
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), unique=True, index=True)
    date = Column(DateTime, default=datetime.now)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"))
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    total = Column(Float, default=0)
    status = Column(String(20), default="draft")
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    items = relationship("PurchaseItem", back_populates="purchase")

class PurchaseItem(Base):
    """Kirim qatorlari"""
    __tablename__ = "purchase_items"
    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Float)
    price = Column(Float)
    total = Column(Float)
    purchase = relationship("Purchase", back_populates="items")



# ==========================================
# FOYDALANUVCHILAR
# ==========================================

class User(Base):
    """Foydalanuvchilar"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    password_hash = Column(String(255))
    full_name = Column(String(100))
    role = Column(String(20), default="user")  # admin, manager, user
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


# ==========================================
# TOVARLAR VA XOM ASHYO
# ==========================================

class Category(Base):
    """Kategoriyalar"""
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)
    name = Column(String(100), index=True)
    type = Column(String(20))  # product, material
    description = Column(Text)
    
    products = relationship("Product", back_populates="category")


class Unit(Base):
    """O'lchov birliklari"""
    __tablename__ = "units"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, index=True)  # kg, dona, l
    name = Column(String(50))  # Kilogram, Dona, Litr
    
    products = relationship("Product", back_populates="unit")


class Product(Base):
    """Mahsulotlar va xom ashyolar"""
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=True, default=None)
    name = Column(String(200), index=True)
    type = Column(String(20))  # product, material (mahsulot yoki xom ashyo)
    category_id = Column(Integer, ForeignKey("categories.id"))
    unit_id = Column(Integer, ForeignKey("units.id"))
    direction_id = Column(Integer, ForeignKey("directions.id"), nullable=True)  # Yo'nalish
    purchase_price = Column(Float, default=0)  # Sotib olish narxi
    sale_price = Column(Float, default=0)  # Sotish narxi
    min_stock = Column(Float, default=0)  # Minimal qoldiq
    barcode = Column(String(50))
    image = Column(String(255))  # Rasm fayli nomi
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    
    category = relationship("Category", back_populates="products")
    unit = relationship("Unit", back_populates="products")
    stock_items = relationship("Stock", back_populates="product")
    recipe_items = relationship("RecipeItem", back_populates="product")


# ==========================================
# OMBORLAR VA QOLDIQLAR
# ==========================================

class Warehouse(Base):
    """Omborlar"""
    __tablename__ = "warehouses"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)
    name = Column(String(100), index=True)
    address = Column(String(255))
    responsible_id = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    
    stocks = relationship("Stock", back_populates="warehouse")


class Stock(Base):
    """Ombor qoldiqlari"""
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Float, default=0)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    warehouse = relationship("Warehouse", back_populates="stocks")
    product = relationship("Product", back_populates="stock_items")


# ==========================================
# ISHLAB CHIQARISH
# ==========================================

class Recipe(Base):
    """Retseptlar (mahsulot tarkibi)"""
    __tablename__ = "recipes"
    
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))  # Qaysi mahsulot uchun
    name = Column(String(200))
    output_quantity = Column(Float, default=1)  # Chiqish miqdori
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    
    items = relationship("RecipeItem", back_populates="recipe")


class RecipeItem(Base):
    """Retsept tarkibi"""
    __tablename__ = "recipe_items"
    
    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"))
    product_id = Column(Integer, ForeignKey("products.id"))  # Xom ashyo
    quantity = Column(Float)  # Miqdori
    
    recipe = relationship("Recipe", back_populates="items")
    product = relationship("Product", back_populates="recipe_items")


class Production(Base):
    """Ishlab chiqarish"""
    __tablename__ = "productions"
    
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), unique=True, index=True)
    date = Column(DateTime, default=datetime.now)
    recipe_id = Column(Integer, ForeignKey("recipes.id"))
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"))
    quantity = Column(Float)  # Ishlab chiqarilgan miqdor
    status = Column(String(20), default="draft")  # draft, completed, cancelled
    user_id = Column(Integer, ForeignKey("users.id"))
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


# ==========================================
# KONTRAGENTLAR (MIJOZLAR, YETKAZUVCHILAR)
# ==========================================

class Partner(Base):
    """Kontragentlar"""
    __tablename__ = "partners"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)
    name = Column(String(200), index=True)
    type = Column(String(20))  # customer, supplier, both
    phone = Column(String(20))
    phone2 = Column(String(20))
    address = Column(String(255))
    inn = Column(String(20))
    balance = Column(Float, default=0)  # Balans (qarzdorlik)
    credit_limit = Column(Float, default=0)  # Kredit limiti
    discount_percent = Column(Float, default=0)  # Chegirma foizi
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    
    orders = relationship("Order", back_populates="partner")
    payments = relationship("Payment", back_populates="partner")


# ==========================================
# BUYURTMALAR VA SOTISH
# ==========================================

class Order(Base):
    """Buyurtmalar va sotuvlar"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), unique=True, index=True)
    date = Column(DateTime, default=datetime.now)
    type = Column(String(20))  # sale, purchase, return_sale, return_purchase
    partner_id = Column(Integer, ForeignKey("partners.id"))
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    subtotal = Column(Float, default=0)  # Jami (chegirmasiz)
    discount_percent = Column(Float, default=0)
    discount_amount = Column(Float, default=0)
    total = Column(Float, default=0)  # Jami (chegirmali)
    paid = Column(Float, default=0)  # To'langan
    debt = Column(Float, default=0)  # Qarz
    status = Column(String(20), default="draft")  # draft, confirmed, completed, cancelled
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    partner = relationship("Partner", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    """Buyurtma qatorlari"""
    __tablename__ = "order_items"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Float)
    price = Column(Float)
    discount_percent = Column(Float, default=0)
    total = Column(Float)
    
    order = relationship("Order", back_populates="items")


# ==========================================
# MOLIYA (KASSA)
# ==========================================

class CashRegister(Base):
    """Kassalar"""
    __tablename__ = "cash_registers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    balance = Column(Float, default=0)
    is_active = Column(Boolean, default=True)


class Payment(Base):
    """To'lovlar"""
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), unique=True, index=True)
    date = Column(DateTime, default=datetime.now)
    type = Column(String(20))  # income, expense (kirim, chiqim)
    cash_register_id = Column(Integer, ForeignKey("cash_registers.id"))
    partner_id = Column(Integer, ForeignKey("partners.id"), nullable=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    amount = Column(Float)
    payment_type = Column(String(20))  # cash, card, transfer
    category = Column(String(50))  # sale, purchase, salary, rent, other
    description = Column(Text)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)
    
    partner = relationship("Partner", back_populates="payments")


# ==========================================
# XODIMLAR
# ==========================================

class Employee(Base):
    """Xodimlar"""
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)
    full_name = Column(String(200), index=True)
    position = Column(String(100))
    department = Column(String(100))  # Eski maydon (deprecated)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)  # Yangi maydon
    phone = Column(String(20))
    address = Column(String(255))
    hire_date = Column(Date)
    salary = Column(Float, default=0)
    is_active = Column(Boolean, default=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    hikvision_id = Column(String(50))  # Hikvision tizimidagi ID
    created_at = Column(DateTime, default=datetime.now)


class Salary(Base):
    """Ish haqi"""
    __tablename__ = "salaries"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"))
    year = Column(Integer)
    month = Column(Integer)
    base_salary = Column(Float, default=0)
    bonus = Column(Float, default=0)
    deduction = Column(Float, default=0)
    total = Column(Float, default=0)
    paid = Column(Float, default=0)
    status = Column(String(20), default="pending")  # pending, paid
    created_at = Column(DateTime, default=datetime.now)


# ==========================================
# SAVDO AGENTLARI
# ==========================================

class Agent(Base):
    """Savdo agentlari"""
    __tablename__ = "agents"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)
    full_name = Column(String(200), index=True)
    phone = Column(String(20))
    telegram_id = Column(String(50))
    photo = Column(String(255))
    region = Column(String(100))  # Hudud
    is_active = Column(Boolean, default=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    locations = relationship("AgentLocation", back_populates="agent")
    routes = relationship("Route", back_populates="agent")
    visits = relationship("Visit", back_populates="agent")


class AgentLocation(Base):
    """Agent joylashuvi (GPS)"""
    __tablename__ = "agent_locations"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    latitude = Column(Float)
    longitude = Column(Float)
    accuracy = Column(Float)  # GPS aniqlik (metr)
    battery = Column(Integer)  # Telefon batareya %
    recorded_at = Column(DateTime, default=datetime.now)
    
    agent = relationship("Agent", back_populates="locations")


# ==========================================
# MARSHRUTLAR
# ==========================================

class Route(Base):
    """Kunlik marshrutlar"""
    __tablename__ = "routes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    agent_id = Column(Integer, ForeignKey("agents.id"))
    day_of_week = Column(Integer)  # 0=Dushanba, 6=Yakshanba
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    
    agent = relationship("Agent", back_populates="routes")
    points = relationship("RoutePoint", back_populates="route")


class RoutePoint(Base):
    """Marshrut nuqtalari"""
    __tablename__ = "route_points"
    
    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"))
    partner_id = Column(Integer, ForeignKey("partners.id"))
    order_num = Column(Integer)  # Tartib raqami
    planned_time = Column(String(10))  # "09:00"
    
    route = relationship("Route", back_populates="points")


# ==========================================
# TASHRIFLAR (VIZITLAR)
# ==========================================

class Visit(Base):
    """Agent tashriflari"""
    __tablename__ = "visits"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(Integer, ForeignKey("agents.id"))
    partner_id = Column(Integer, ForeignKey("partners.id"))
    visit_date = Column(DateTime, default=datetime.now)
    latitude = Column(Float)
    longitude = Column(Float)
    check_in_time = Column(DateTime)
    check_out_time = Column(DateTime)
    status = Column(String(20))  # planned, visited, skipped
    notes = Column(Text)
    photo = Column(String(255))
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    
    agent = relationship("Agent", back_populates="visits")


# ==========================================
# YETKAZIB BERISH
# ==========================================

class Driver(Base):
    """Haydovchilar/Yetkazib beruvchilar"""
    __tablename__ = "drivers"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)
    full_name = Column(String(200), index=True)
    phone = Column(String(20))
    telegram_id = Column(String(50))
    vehicle_number = Column(String(20))  # Mashina raqami
    vehicle_type = Column(String(50))  # Mashina turi
    is_active = Column(Boolean, default=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    locations = relationship("DriverLocation", back_populates="driver")
    deliveries = relationship("Delivery", back_populates="driver")


class DriverLocation(Base):
    """Haydovchi joylashuvi (GPS)"""
    __tablename__ = "driver_locations"
    
    id = Column(Integer, primary_key=True, index=True)
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    latitude = Column(Float)
    longitude = Column(Float)
    speed = Column(Float)  # Tezlik km/s
    recorded_at = Column(DateTime, default=datetime.now)
    
    driver = relationship("Driver", back_populates="locations")


class Delivery(Base):
    """Yetkazib berishlar"""
    __tablename__ = "deliveries"
    
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), unique=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    order_number = Column(String(50))  # Buyurtma raqami (qo'lda kiritish uchun)
    delivery_address = Column(String(500))  # Yetkazish manzili
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    status = Column(String(20), default="pending")  # pending, in_progress, delivered, failed
    planned_date = Column(DateTime)
    delivered_at = Column(DateTime)
    latitude = Column(Float)  # Yetkazilgan joy
    longitude = Column(Float)
    photo = Column(String(255))  # Tasdiqlash rasmi
    signature = Column(String(255))  # Imzo
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    
    driver = relationship("Driver", back_populates="deliveries")


# ==========================================
# MIJOZ LOKATSIYALARI
# ==========================================

class PartnerLocation(Base):
    """Mijoz/do'kon manzili"""
    __tablename__ = "partner_locations"
    
    id = Column(Integer, primary_key=True, index=True)
    partner_id = Column(Integer, ForeignKey("partners.id"))
    name = Column(String(100))  # "Asosiy do'kon", "Filial 1"
    address = Column(String(255))
    latitude = Column(Float)
    longitude = Column(Float)
    is_primary = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


# ==========================================
# BO'LIMLAR VA YO'NALISHLAR
# ==========================================

class Department(Base):
    """Bo'limlar (Ishlab chiqarish, Savdo, Boshqaruv, ...)"""
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)
    name = Column(String(100), index=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class Direction(Base):
    """Yo'nalishlar (Halva, Konfet, Shirinlik, ...)"""
    __tablename__ = "directions"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)
    name = Column(String(100), index=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


# Bazani yaratish
def init_db():
    Base.metadata.create_all(bind=engine)
    print("✅ Database yaratildi!")


if __name__ == "__main__":
    init_db()
