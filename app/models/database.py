from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Date, UniqueConstraint
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from datetime import datetime
import os

Base = declarative_base()

# Loyiha ildizidagi baza (qayerdan ishga tushirilmasa ham bir xil fayl)
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_db_path = os.path.join(_root, "totli_holva.db")
DATABASE_URL = f"sqlite:///{_db_path}"

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
    total_expenses = Column(Float, default=0)  # Xarajatlar jami (so'm)
    status = Column(String(20), default="draft")
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    items = relationship("PurchaseItem", back_populates="purchase")
    expenses = relationship("PurchaseExpense", back_populates="purchase")
    partner = relationship("Partner")
    warehouse = relationship("Warehouse")

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
    product = relationship("Product")


class PurchaseExpense(Base):
    """Tovar kirimi xarajatlari"""
    __tablename__ = "purchase_expenses"
    id = Column(Integer, primary_key=True, index=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"))
    name = Column(String(200))   # Xarajat turi/nomi (yo'l, yuk, boj, ...)
    amount = Column(Float)       # Summa (so'm)
    created_at = Column(DateTime, default=datetime.now)

    purchase = relationship("Purchase", back_populates="expenses")


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
    product_prices = relationship("ProductPrice", back_populates="product", cascade="all, delete-orphan")


class PriceType(Base):
    """Narx turlari (Chakana, Ulgurji, VIP va h.k.) — har bir mijoz turi uchun narx"""
    __tablename__ = "price_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, index=True, nullable=True)
    is_active = Column(Boolean, default=True)
    product_prices = relationship("ProductPrice", back_populates="price_type")


class ProductPrice(Base):
    """Mahsulot narxi narx turi bo'yicha (har bir tur uchun alohida sotuv narxi)"""
    __tablename__ = "product_prices"
    __table_args__ = (UniqueConstraint("product_id", "price_type_id", name="uq_product_price_type"),)
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    price_type_id = Column(Integer, ForeignKey("price_types.id"), nullable=False)
    sale_price = Column(Float, default=0)
    product = relationship("Product", back_populates="product_prices")
    price_type = relationship("PriceType", back_populates="product_prices")


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
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)  # Bo'limga biriktirish
    is_active = Column(Boolean, default=True)
    
    stocks = relationship("Stock", back_populates="warehouse")
    department = relationship("Department")


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
    movements = relationship("StockMovement", back_populates="stock", order_by="StockMovement.created_at.desc()")


class StockMovement(Base):
    """Ombor harakati - har bir operatsiya uchun hujjat"""
    __tablename__ = "stock_movements"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=True)  # null bo'lishi mumkin (yangi qoldiq)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    
    # Operatsiya turi va hujjat
    operation_type = Column(String(50), nullable=False)  # purchase, production, transfer_in, transfer_out, sale, adjustment, other
    document_type = Column(String(50), nullable=False)  # Purchase, Production, WarehouseTransfer, Sale, StockAdjustmentDoc
    document_id = Column(Integer, nullable=False)  # Hujjat ID
    document_number = Column(String(100), nullable=True)  # Hujjat raqami (ko'rsatish uchun)
    
    # Harakat miqdori
    quantity_change = Column(Float, nullable=False)  # O'zgarish miqdori (+ kirim, - chiqim)
    quantity_after = Column(Float, nullable=False)  # O'zgarishdan keyingi qoldiq
    
    # Qo'shimcha ma'lumotlar
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Operatsiyani bajargan foydalanuvchi
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    
    # Relationships
    stock = relationship("Stock", back_populates="movements")
    warehouse = relationship("Warehouse")
    product = relationship("Product")
    user = relationship("User")


class WarehouseTransfer(Base):
    """Ombordan omborga o'tkazish hujjati"""
    __tablename__ = "warehouse_transfers"
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), unique=True, index=True)
    date = Column(DateTime, default=datetime.now)
    from_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    to_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=False)
    status = Column(String(20), default="draft")  # draft, pending_approval, confirmed
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Yaratgan foydalanuvchi
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Tasdiqlagan foydalanuvchi (bo'lim foydalanuvchisi)
    approved_at = Column(DateTime, nullable=True)  # Tasdiqlash vaqti
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    from_warehouse = relationship("Warehouse", foreign_keys=[from_warehouse_id])
    to_warehouse = relationship("Warehouse", foreign_keys=[to_warehouse_id])
    user = relationship("User", foreign_keys=[user_id])
    approved_by = relationship("User", foreign_keys=[approved_by_user_id])
    items = relationship("WarehouseTransferItem", back_populates="transfer", cascade="all, delete-orphan")


class WarehouseTransferItem(Base):
    """Ombordan omborga o'tkazish hujjati qatori"""
    __tablename__ = "warehouse_transfer_items"
    id = Column(Integer, primary_key=True, index=True)
    transfer_id = Column(Integer, ForeignKey("warehouse_transfers.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Float, default=0)

    transfer = relationship("WarehouseTransfer", back_populates="items")
    product = relationship("Product")


# ==========================================
# TOVAR QOLDIQ HUJJATI (1C uslubida)
# ==========================================

class StockAdjustmentDoc(Base):
    """Tovar qoldiqlari hujjati (bitta hujjat — bir nechta qator)"""
    __tablename__ = "stock_adjustment_docs"
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), unique=True, index=True)
    date = Column(DateTime, default=datetime.now)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="draft")  # draft, confirmed
    total_tannarx = Column(Float, default=0)   # Jami summa tannarx (so'm)
    total_sotuv = Column(Float, default=0)     # Jami sotuv summa (so'm)
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User")
    items = relationship("StockAdjustmentDocItem", back_populates="doc", cascade="all, delete-orphan")


class StockAdjustmentDocItem(Base):
    """Tovar qoldiq hujjati qatori"""
    __tablename__ = "stock_adjustment_doc_items"
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey("stock_adjustment_docs.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"))
    quantity = Column(Float)
    cost_price = Column(Float, default=0)   # Tannarx (so'm)
    sale_price = Column(Float, default=0)     # Sotuv narxi (so'm)

    doc = relationship("StockAdjustmentDoc", back_populates="items")
    product = relationship("Product")
    warehouse = relationship("Warehouse")


# ==========================================
# KASSA QOLDIQ HUJJATI (1C uslubida)
# ==========================================

class CashBalanceDoc(Base):
    """Kassa qoldiqlari hujjati"""
    __tablename__ = "cash_balance_docs"
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), unique=True, index=True)
    date = Column(DateTime, default=datetime.now)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="draft")  # draft, confirmed
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User")
    items = relationship("CashBalanceDocItem", back_populates="doc", cascade="all, delete-orphan")


class CashBalanceDocItem(Base):
    """Kassa qoldiq hujjati qatori — bitta kassa, yangi balans"""
    __tablename__ = "cash_balance_doc_items"
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey("cash_balance_docs.id"))
    cash_register_id = Column(Integer, ForeignKey("cash_registers.id"))
    balance = Column(Float, default=0)
    previous_balance = Column(Float, default=None)  # Tasdiqdan oldingi balans (revert uchun)

    doc = relationship("CashBalanceDoc", back_populates="items")
    cash_register = relationship("CashRegister")


# ==========================================
# KONTRAGENT QOLDIQ HUJJATI (1C uslubida)
# ==========================================

class PartnerBalanceDoc(Base):
    """Kontragent qoldiqlari (balans) hujjati"""
    __tablename__ = "partner_balance_docs"
    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), unique=True, index=True)
    date = Column(DateTime, default=datetime.now)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String(20), default="draft")  # draft, confirmed
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User")
    items = relationship("PartnerBalanceDocItem", back_populates="doc", cascade="all, delete-orphan")


class PartnerBalanceDocItem(Base):
    """Kontragent balans hujjati qatori"""
    __tablename__ = "partner_balance_doc_items"
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey("partner_balance_docs.id"))
    partner_id = Column(Integer, ForeignKey("partners.id"))
    balance = Column(Float, default=0)
    previous_balance = Column(Float, default=None)  # Tasdiqdan oldingi balans (revert uchun)

    doc = relationship("PartnerBalanceDoc", back_populates="items")
    partner = relationship("Partner")


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
    
    product = relationship("Product")
    items = relationship("RecipeItem", back_populates="recipe")
    stages = relationship("RecipeStage", back_populates="recipe", order_by="RecipeStage.stage_number", cascade="all, delete-orphan")


class RecipeStage(Base):
    """Retseptga bog'langan ishlab chiqarish bosqichlari"""
    __tablename__ = "recipe_stages"
    __table_args__ = (UniqueConstraint("recipe_id", "stage_number", name="uq_recipe_stage_number"),)

    id = Column(Integer, primary_key=True, index=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    stage_number = Column(Integer, nullable=False)
    name = Column(String(200), nullable=False)

    recipe = relationship("Recipe", back_populates="stages")


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
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"))  # 1-ombor: xom ashyo ombori (material shu yerdan olinadi)
    output_warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)  # 2-ombor: yarim tayyor ombori (mahsulot shu yerga yoziladi)
    quantity = Column(Float)  # Ishlab chiqarilgan miqdor (o'zgarmaydi)
    status = Column(String(20), default="draft")  # draft, in_progress, completed, cancelled
    current_stage = Column(Integer, default=1)  # joriy bosqich (1 dan max_stage gacha)
    max_stage = Column(Integer, nullable=True)   # retseptdagi bosqichlar soni (yoki 4)
    user_id = Column(Integer, ForeignKey("users.id"))
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=True)  # Qaysi uskunda (oxirgi bosqich)
    operator_id = Column(Integer, ForeignKey("employees.id"), nullable=True)  # Operator (xodim)
    note = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

    recipe = relationship("Recipe")
    warehouse = relationship("Warehouse", foreign_keys=[warehouse_id])
    machine = relationship("Machine")
    operator = relationship("Employee", foreign_keys=[operator_id])
    output_warehouse = relationship("Warehouse", foreign_keys=[output_warehouse_id])
    production_items = relationship("ProductionItem", back_populates="production", cascade="all, delete-orphan")
    stages = relationship("ProductionStage", back_populates="production", cascade="all, delete-orphan", order_by="ProductionStage.stage_number")


class ProductionItem(Base):
    """Ishlab chiqarish buyurtmasidagi xom ashyo miqdori (shu buyurtma uchun tahrirlanadi, retsept o'zgarmaydi)"""
    __tablename__ = "production_items"
    
    id = Column(Integer, primary_key=True, index=True)
    production_id = Column(Integer, ForeignKey("productions.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Float)  # Shu buyurtma uchun ishlatiladigan miqdor (kg)

    production = relationship("Production", back_populates="production_items")
    product = relationship("Product")


# Ishlab chiqarish 4 bosqichi: 1) qiyom 2) qiyomga qo'shimchalar → yarim tayyor 3) holva kesish 4) qadoqlash
PRODUCTION_STAGE_NAMES = {
    1: "Qiyom tayyorlash",
    2: "Qiyomga qo'shiladigan mahsulotlar, yarim tayyor",
    3: "Holva kesish",
    4: "Qadoqlash",
}


class ProductionStage(Base):
    """Ishlab chiqarish buyurtmasining har bir bosqichi (1–4)"""
    __tablename__ = "production_stages"

    id = Column(Integer, primary_key=True, index=True)
    production_id = Column(Integer, ForeignKey("productions.id"), nullable=False)
    stage_number = Column(Integer, nullable=False)  # 1, 2, 3, 4
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=True)
    operator_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    quantity_in = Column(Float, nullable=True)   # Kiruvchi miqdor (kg)
    quantity_out = Column(Float, nullable=True)  # Chiquvchi miqdor (kg)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    production = relationship("Production", back_populates="stages")
    machine = relationship("Machine")
    operator = relationship("Employee", foreign_keys=[operator_id])


class Machine(Base):
    """Ishlab chiqarish uskunalari"""
    __tablename__ = "machines"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)
    name = Column(String(200), index=True)
    machine_type = Column(String(100))  # mixer, oven, packaging, etc.
    status = Column(String(20), default="idle")  # idle, active, maintenance, broken
    operator_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    warehouse_id = Column(Integer, ForeignKey("warehouses.id"), nullable=True)
    capacity = Column(Float)  # Maximum capacity per hour
    efficiency = Column(Float, default=100.0)  # Current efficiency percentage
    last_maintenance = Column(DateTime, nullable=True)
    next_maintenance = Column(DateTime, nullable=True)
    notes = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    
    operator = relationship("Employee", foreign_keys=[operator_id])


# ==========================================
# KONTRAGENTLAR (MIJOZLAR, YETKAZUVCHILAR)
# ==========================================

class Partner(Base):
    """Kontragentlar"""
    __tablename__ = "partners"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)
    name = Column(String(200), index=True)  # Savdo nuqtasi nomi
    legal_name = Column(String(200), nullable=True)  # Yuridik nomi
    type = Column(String(20))  # customer, supplier, both
    
    # Contact Information
    contact_person = Column(String(100), nullable=True)  # Aloqa shaxsi
    phone = Column(String(20))
    phone2 = Column(String(20), nullable=True)  # Qo'shimcha telefon
    
    # Address
    address = Column(String(255))
    landmark = Column(String(255), nullable=True)  # Mo'ljal
    
    # Location
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Business Details
    visit_day = Column(Integer, nullable=True)  # Tashrif kuni (0-6)
    category = Column(String(10), nullable=True)  # A, B, C, D
    region = Column(String(50), nullable=True)  # Hudud
    customer_type = Column(String(50), nullable=True)  # retail, wholesale, horeca, distributor
    sales_channel = Column(String(50), nullable=True)  # direct, distributor, online
    product_categories = Column(String(100), nullable=True)  # food, drinks, household, cosmetics
    
    # Financial
    inn = Column(String(20), nullable=True)
    balance = Column(Float, default=0)  # Balans (qarzdorlik)
    credit_limit = Column(Float, default=0)  # Kredit limiti
    discount_percent = Column(Float, default=0)  # Chegirma foizi
    
    # Requisites
    account = Column(String(50), nullable=True)  # Hisob raqami
    bank = Column(String(100), nullable=True)  # Bank
    mfo = Column(String(20), nullable=True)  # MFO
    oked = Column(String(20), nullable=True)  # OKED
    pinfl = Column(String(20), nullable=True)  # PINFL
    contract_number = Column(String(50), nullable=True)  # Shartnoma raqami
    contract_date = Column(Date, nullable=True)  # Shartnoma sanasi
    
    # Other
    notes = Column(Text, nullable=True)  # Izoh
    photo = Column(String(255), nullable=True)  # Rasm fayli nomi
    agent_id = Column(Integer, nullable=True)  # Qaysi agent qo'shgan
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
    price_type_id = Column(Integer, ForeignKey("price_types.id"), nullable=True)  # Sotuvda qaysi narx turi ishlatiladi
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
    price_type = relationship("PriceType")


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
    product = relationship("Product")


# ==========================================
# MOLIYA (KASSA)
# ==========================================

class CashRegister(Base):
    """Kassalar"""
    __tablename__ = "cash_registers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    balance = Column(Float, default=0)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)  # Bo'limga biriktirish
    is_active = Column(Boolean, default=True)
    
    department = relationship("Department")


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
    birth_date = Column(Date, nullable=True)  # Tug'ilgan kun (bosh sahifa bildirishnomalari uchun)
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
    
    locations = relationship("AgentLocation", back_populates="agent", order_by="AgentLocation.recorded_at.desc()")
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
    accuracy = Column(Float)  # GPS accuracy in meters
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
    accuracy = Column(Float)  # GPS aniqlik (metr)
    battery = Column(Integer)  # Telefon batareya %
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
    
    # Relationships
    warehouses = relationship("Warehouse", backref="warehouse_department")
    cash_registers = relationship("CashRegister", backref="cash_department")


class Direction(Base):
    """Yo'nalishlar (Halva, Konfet, Shirinlik, ...)"""
    __tablename__ = "directions"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)
    name = Column(String(100), index=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class Position(Base):
    """Lavozimlar"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)
    name = Column(String(100), index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


class Region(Base):
    """Hududlar (Toshkent, Samarqand, Buxoro, ...)"""
    __tablename__ = "regions"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)
    name = Column(String(100), index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)


# ==========================================
# BILDIRISHNOMALAR (NOTIFICATIONS)
# ==========================================

class Notification(Base):
    """Tizim bildirish nomalari"""
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null = all users
    title = Column(String(200))
    message = Column(Text)
    notification_type = Column(String(50))  # info, warning, error, success
    priority = Column(String(20), default="normal")  # low, normal, high, urgent
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    action_url = Column(String(500), nullable=True)  # Optional link
    related_entity_type = Column(String(50), nullable=True)  # order, delivery, stock, etc.
    related_entity_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime, nullable=True)


# Bazani yaratish — faqat jadvallar yaratiladi, mavjud ma'lumotlar o'chirilmaydi (saqlanadi)
def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database tayyor (mavjud ma'lumotlar saqlanadi).")


if __name__ == "__main__":
    init_db()
