
# --- Barcha importlar ---

from fastapi import FastAPI, Request, Depends, HTTPException, Form, Cookie, File, UploadFile
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, Response, StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uvicorn
import barcode
from barcode.writer import ImageWriter
from PIL import Image
import os
from typing import Optional
import openpyxl
import io
from app.models.database import (
    get_db, init_db, 
    User, Product, Category, Unit, Warehouse, Stock,
    Partner, Order, OrderItem, Payment, CashRegister,
    Recipe, RecipeItem, Production, Employee, Salary,
    Agent, AgentLocation, Route, RoutePoint, Visit,
    Driver, DriverLocation, Delivery, PartnerLocation,
    Purchase, PurchaseItem, Department, Direction
)
from app.utils.auth import (
    hash_password, verify_password, 
    create_session_token, get_user_from_token
)

app = FastAPI(title="TOTLI HOLVA", description="Biznes boshqaruv tizimi", version="1.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# ==========================================
# AUTENTIFIKATSIYA HELPER FUNKSIYALARI
# ==========================================

def get_current_user(session_token: Optional[str] = Cookie(None), db: Session = Depends(get_db)) -> Optional[User]:
    """Cookie dan foydalanuvchini olish"""
    if not session_token:
        return None
    
    user_data = get_user_from_token(session_token)
    if not user_data:
        return None
    
    user = db.query(User).filter(User.id == user_data["user_id"]).first()
    if not user or not user.is_active:
        return None
    
    return user


def require_auth(current_user: User = Depends(get_current_user)) -> Optional[User]:
    """Login talab qilish - None qaytaradi agar login qilmagan bo'lsa"""
    return current_user


# ==========================================
# AUTENTIFIKATSIYA ENDPOINTLARI
# ==========================================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, current_user: User = Depends(get_current_user)):
    """Login sahifasi"""
    # Agar foydalanuvchi allaqachon tizimga kirgan bo'lsa, bosh sahifaga yo'naltirish
    if current_user:
        return RedirectResponse(url="/", status_code=303)
    
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Login qilish"""
    try:
        # Foydalanuvchini topish
        user = db.query(User).filter(User.username == username).first()
        
        # Parolni tekshirish
        if not user or not verify_password(password, user.password_hash):
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Login yoki parol noto'g'ri!"
            })
        
        # Faol emasligini tekshirish
        if not user.is_active:
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Sizning hisobingiz faol emas. Administrator bilan bog'laning."
            })
        
        # Session token yaratish
        token = create_session_token(user.id, user.username)
        print(f"✅ Token yaratildi: {token[:50]}...")
        
        # Cookie o'rnatish
        redirect_response = RedirectResponse(url="/", status_code=303)
        redirect_response.set_cookie(
            key="session_token",
            value=token,
            path="/",
            httponly=True,
            max_age=86400,  # 24 soat
            samesite="lax",
            secure=False  # HTTP uchun False bo'lishi kerak
        )
        print(f"✅ Cookie o'rnatildi. Redirect: /")
        
        return redirect_response
    
    except Exception as e:
        print(f"❌ LOGIN XATO: {str(e)}")
        import traceback
        traceback.print_exc()
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": f"Tizimda xatolik yuz berdi: {str(e)}"
        })


@app.get("/logout")
async def logout():
    """Logout qilish"""
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("session_token")
    return response


# ==========================================
# ASOSIY SAHIFALAR
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Bosh sahifa - Dashboard"""
    try:
        # Debug log
        with open("debug_home.log", "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Time: {datetime.now()}\n")
            f.write(f"User: {current_user}\n")
        
        # Agar login qilmagan bo'lsa, login sahifasiga yo'naltirish
        if not current_user:
            with open("debug_home.log", "a", encoding="utf-8") as f:
                f.write("⚠️ User not authenticated, redirecting to login\n")
            return RedirectResponse(url="/login", status_code=303)
        
        with open("debug_home.log", "a", encoding="utf-8") as f:
            f.write(f"✅ User authenticated: {current_user.username}\n")
        
        # Statistika
        stats = {
            "tayyor_count": db.query(Product).filter(Product.type == "tayyor").count(),
            "yarim_tayyor_count": db.query(Product).filter(Product.type == "yarim_tayyor").count(),
            "hom_ashyo_count": db.query(Product).filter(Product.type == "hom_ashyo").count(),
            "partners_count": db.query(Partner).count(),
            "employees_count": db.query(Employee).count(),
        }
        
        with open("debug_home.log", "a", encoding="utf-8") as f:
            f.write(f"Stats 1: {stats}\n")
        
        # Bugungi savdo
        today = datetime.now().date()
        today_sales = db.query(Order).filter(
            Order.type == "sale",
            Order.date >= today
        ).all()
        stats["today_sales"] = sum(s.total_amount for s in today_sales)
        stats["today_orders"] = len(today_sales)
        
        with open("debug_home.log", "a", encoding="utf-8") as f:
            f.write(f"Stats 2: today_sales calculated\n")
        
        # Kassa qoldig'i
        cash = db.query(CashRegister).first()
        stats["cash_balance"] = cash.balance if cash else 0
        
        # Qarzdorlar
        debtors = db.query(Partner).filter(Partner.balance > 0).all()
        stats["total_debt"] = sum(p.balance for p in debtors)
        
        with open("debug_home.log", "a", encoding="utf-8") as f:
            f.write(f"✅ Stats calculated, rendering template\n")
        
        return templates.TemplateResponse("index.html", {
            "request": request,
            "stats": stats,
            "current_user": current_user,
            "page_title": "Bosh sahifa"
        })
    except Exception as e:
        with open("debug_home.log", "a", encoding="utf-8") as f:
            f.write(f"❌ HOME PAGE XATO: {str(e)}\n")
            import traceback
            f.write(traceback.format_exc())
        raise


# ==========================================
# MA'LUMOTLAR BO'LIMI
# ==========================================
@app.get("/info", response_class=HTMLResponse)
async def info_index(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Ma'lumotlar bo'limi"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse("info/index.html", {"request": request, "current_user": current_user, "page_title": "Ma'lumotlar"})

# Omborlar bo'limi
@app.get("/info/warehouses", response_class=HTMLResponse)
async def info_warehouses(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Omborlar ro'yxati"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    warehouses = db.query(Warehouse).all()
    return templates.TemplateResponse("info/warehouses.html", {"request": request, "warehouses": warehouses, "current_user": current_user, "page_title": "Omborlar"})

@app.post("/info/warehouses/add")
async def info_warehouses_add(
    request: Request,
    name: str = Form(...),
    address: str = Form(""),
    db: Session = Depends(get_db)
):
    # Dublikat tekshiruvi - nom bo'yicha
    existing_by_name = db.query(Warehouse).filter(Warehouse.name == name).first()
    if existing_by_name:
        raise HTTPException(status_code=400, detail=f"'{name}' nomli ombor allaqachon mavjud!")
    
    warehouse = Warehouse(name=name, code=None, address=address, is_active=True)
    db.add(warehouse)
    db.commit()
    return RedirectResponse(url="/info/warehouses", status_code=303)

@app.post("/info/warehouses/edit/{warehouse_id}")
async def info_warehouses_edit(
    warehouse_id: int,
    name: str = Form(...),
    address: str = Form(""),
    db: Session = Depends(get_db)
):
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Ombor topilmadi")
    
    # Dublikat tekshiruvi - nom bo'yicha (o'zidan boshqa)
    existing_by_name = db.query(Warehouse).filter(
        Warehouse.name == name,
        Warehouse.id != warehouse_id
    ).first()
    if existing_by_name:
        raise HTTPException(status_code=400, detail=f"'{name}' nomli ombor allaqachon mavjud!")
    
    warehouse.name = name
    warehouse.address = address
    
    db.commit()
    return RedirectResponse(url="/info/warehouses", status_code=303)

@app.post("/info/warehouses/delete/{warehouse_id}")
async def info_warehouses_delete(warehouse_id: int, db: Session = Depends(get_db)):
    warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not warehouse:
        raise HTTPException(status_code=404, detail="Ombor topilmadi")
    
    db.delete(warehouse)
    db.commit()
    return RedirectResponse(url="/info/warehouses", status_code=303)

# --- WAREHOUSE EXCEL OPERATIONS ---
@app.get("/info/warehouses/export")
async def export_warehouses(db: Session = Depends(get_db)):
    warehouses = db.query(Warehouse).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Warehouses"
    ws.append(["ID", "Kod", "Nomi", "Manzil"])
    for w in warehouses:
        ws.append([w.id, w.code, w.name, w.address])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=omborlar.xlsx"})

@app.get("/info/warehouses/template")
async def template_warehouses():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"
    ws.append(["Kod", "Nomi", "Manzil"])
    ws.append(["MAIN", "Asosiy ombor", "Toshkent sh."])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=ombor_andoza.xlsx"})

@app.post("/info/warehouses/import")
async def import_warehouses(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(contents))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for row in rows:
        if not row[0]: continue
        code, name, address = row[0], row[1], row[2]
        warehouse = db.query(Warehouse).filter(Warehouse.code == code).first()
        if not warehouse:
            warehouse = Warehouse(code=code, name=name, address=address)
            db.add(warehouse)
        else:
            warehouse.name = name
            warehouse.address = address
        db.commit()
    return RedirectResponse(url="/info/warehouses", status_code=303)

# O'lchov birliklari bo'limi
@app.get("/info/units", response_class=HTMLResponse)
async def info_units(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    units = db.query(Unit).all()
    return templates.TemplateResponse("info/units.html", {"request": request, "units": units, "current_user": current_user, "page_title": "O'lchov birliklari"})

@app.post("/info/units/add")
async def info_units_add(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(Unit).filter(Unit.code == code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{code}' kodli o'lchov birligi allaqachon mavjud!")
    
    unit = Unit(code=code, name=name)
    db.add(unit)
    db.commit()
    return RedirectResponse(url="/info/units", status_code=303)

@app.post("/info/units/edit/{unit_id}")
async def info_units_edit(
    unit_id: int,
    code: str = Form(...),
    name: str = Form(...),
    db: Session = Depends(get_db)
):
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="O'lchov birligi topilmadi")
    
    existing = db.query(Unit).filter(Unit.code == code, Unit.id != unit_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{code}' kodli o'lchov birligi allaqachon mavjud!")
    
    unit.code = code
    unit.name = name
    db.commit()
    return RedirectResponse(url="/info/units", status_code=303)

@app.post("/info/units/delete/{unit_id}")
async def info_units_delete(unit_id: int, db: Session = Depends(get_db)):
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="O'lchov birligi topilmadi")
    
    db.delete(unit)
    db.commit()
    return RedirectResponse(url="/info/units", status_code=303)

# --- UNITS EXCEL OPERATIONS ---
@app.get("/info/units/export")
async def export_units(db: Session = Depends(get_db)):
    units = db.query(Unit).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Units"
    ws.append(["ID", "Kod", "Nomi"])
    for u in units:
        ws.append([u.id, u.code, u.name])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=olchov_birliklari.xlsx"})

@app.get("/info/units/template")
async def template_units():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"
    ws.append(["Kod", "Nomi"])
    ws.append(["kg", "Kilogramm"])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=birlik_andoza.xlsx"})

@app.post("/info/units/import")
async def import_units(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(contents))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for row in rows:
        if not row[0]: continue
        code, name = row[0], row[1]
        unit = db.query(Unit).filter(Unit.code == code).first()
        if not unit:
            unit = Unit(code=code, name=name)
            db.add(unit)
        else:
            unit.name = name
        db.commit()
    return RedirectResponse(url="/info/units", status_code=303)

# Kategoriyalar bo'limi
@app.get("/info/categories", response_class=HTMLResponse)
async def info_categories(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    categories = db.query(Category).all()
    return templates.TemplateResponse("info/categories.html", {"request": request, "categories": categories, "current_user": current_user, "page_title": "Kategoriyalar"})

@app.post("/info/categories/add")
async def info_categories_add(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    type: str = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(Category).filter(Category.code == code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{code}' kodli kategoriya allaqachon mavjud!")
    
    category = Category(code=code, name=name, type=type)
    db.add(category)
    db.commit()
    return RedirectResponse(url="/info/categories", status_code=303)

@app.post("/info/categories/edit/{category_id}")
async def info_categories_edit(
    category_id: int,
    code: str = Form(...),
    name: str = Form(...),
    type: str = Form(...),
    db: Session = Depends(get_db)
):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")
    
    existing = db.query(Category).filter(Category.code == code, Category.id != category_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{code}' kodli kategoriya allaqachon mavjud!")
    
    category.code = code
    category.name = name
    category.type = type
    db.commit()
    return RedirectResponse(url="/info/categories", status_code=303)

@app.post("/info/categories/delete/{category_id}")
async def info_categories_delete(category_id: int, db: Session = Depends(get_db)):
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")
    
    db.delete(category)
    db.commit()
    return RedirectResponse(url="/info/categories", status_code=303)

# --- CATEGORIES EXCEL OPERATIONS ---
@app.get("/info/categories/export")
async def export_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Categories"
    ws.append(["ID", "Kod", "Nomi", "Turi"])
    for c in categories:
        ws.append([c.id, c.code, c.name, c.type])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=kategoriyalar.xlsx"})

@app.get("/info/categories/template")
async def template_categories():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"
    ws.append(["Kod", "Nomi", "Turi"])
    ws.append(["CAT001", "Shirinliklar", "tayyor"])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=kategoriya_andoza.xlsx"})

@app.post("/info/categories/import")
async def import_categories(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(contents))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for row in rows:
        if not row[0]: continue
        code, name, type_ = row[0], row[1], row[2]
        category = db.query(Category).filter(Category.code == code).first()
        if not category:
            category = Category(code=code, name=name, type=type_)
            db.add(category)
        else:
            category.name = name
            category.type = type_
        db.commit()
    return RedirectResponse(url="/info/categories", status_code=303)
    db.commit()
    return RedirectResponse(url="/info/categories", status_code=303)

# Kassalar bo'limi
@app.get("/info/cash", response_class=HTMLResponse)
async def info_cash(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    cash_registers = db.query(CashRegister).all()
    return templates.TemplateResponse("info/cash.html", {"request": request, "cash_registers": cash_registers, "current_user": current_user, "page_title": "Kassalar"})

@app.post("/info/cash/add")
async def info_cash_add(
    request: Request,
    name: str = Form(...),
    balance: float = Form(0),
    db: Session = Depends(get_db)
):
    cash = CashRegister(name=name, balance=balance, is_active=True)
    db.add(cash)
    db.commit()
    return RedirectResponse(url="/info/cash", status_code=303)

@app.post("/info/cash/edit/{cash_id}")
async def info_cash_edit(
    cash_id: int,
    name: str = Form(...),
    balance: float = Form(0),
    db: Session = Depends(get_db)
):
    cash = db.query(CashRegister).filter(CashRegister.id == cash_id).first()
    if not cash:
        raise HTTPException(status_code=404, detail="Kassa topilmadi")
    
    cash.name = name
    cash.balance = balance
    db.commit()
    return RedirectResponse(url="/info/cash", status_code=303)

@app.post("/info/cash/delete/{cash_id}")
async def info_cash_delete(cash_id: int, db: Session = Depends(get_db)):
    cash = db.query(CashRegister).filter(CashRegister.id == cash_id).first()
    if not cash:
        raise HTTPException(status_code=404, detail="Kassa topilmadi")
    
    db.delete(cash)
    db.commit()
    return RedirectResponse(url="/info/cash", status_code=303)

# Bo'limlar bo'limi
@app.get("/info/departments", response_class=HTMLResponse)
async def info_departments(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    departments = db.query(Department).all()
    return templates.TemplateResponse("info/departments.html", {"request": request, "departments": departments, "current_user": current_user, "page_title": "Bo'limlar"})

@app.post("/info/departments/add")
async def info_departments_add(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    existing = db.query(Department).filter(Department.code == code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{code}' kodli bo'lim allaqachon mavjud!")
    
    department = Department(code=code, name=name, description=description, is_active=True)
    db.add(department)
    db.commit()
    return RedirectResponse(url="/info/departments", status_code=303)

@app.post("/info/departments/edit/{department_id}")
async def info_departments_edit(
    department_id: int,
    code: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Bo'lim topilmadi")
    
    existing = db.query(Department).filter(Department.code == code, Department.id != department_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{code}' kodli bo'lim allaqachon mavjud!")
    
    department.code = code
    department.name = name
    department.description = description
    db.commit()
    return RedirectResponse(url="/info/departments", status_code=303)

@app.post("/info/departments/delete/{department_id}")
async def info_departments_delete(department_id: int, db: Session = Depends(get_db)):
    department = db.query(Department).filter(Department.id == department_id).first()
    if not department:
        raise HTTPException(status_code=404, detail="Bo'lim topilmadi")
    
    db.delete(department)
    db.commit()
    return RedirectResponse(url="/info/departments", status_code=303)

# --- DEPARTMENTS EXCEL OPERATIONS ---
@app.get("/info/departments/export")
async def export_departments(db: Session = Depends(get_db)):
    departments = db.query(Department).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Departments"
    ws.append(["ID", "Kod", "Nomi", "Izoh"])
    for d in departments:
        ws.append([d.id, d.code, d.name, d.description])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=bolimlar.xlsx"})

@app.get("/info/departments/template")
async def template_departments():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"
    ws.append(["Kod", "Nomi", "Izoh"])
    ws.append(["DEP001", "Ishlab chiqarish", "Asosiy tsex"])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=bolim_andoza.xlsx"})

@app.post("/info/departments/import")
async def import_departments(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(contents))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for row in rows:
        if not row[0]: continue
        code, name, description = row[0], row[1], row[2]
        department = db.query(Department).filter(Department.code == code).first()
        if not department:
            department = Department(code=code, name=name, description=description)
            db.add(department)
        else:
            department.name = name
            department.description = description
        db.commit()
    return RedirectResponse(url="/info/departments", status_code=303)

# Yo'nalishlar bo'limi
@app.get("/info/directions", response_class=HTMLResponse)
async def info_directions(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    directions = db.query(Direction).all()
    return templates.TemplateResponse("info/directions.html", {"request": request, "directions": directions, "current_user": current_user, "page_title": "Yo'nalishlar"})

@app.post("/info/directions/add")
async def info_directions_add(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    existing = db.query(Direction).filter(Direction.code == code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{code}' kodli yo'nalish allaqachon mavjud!")
    
    direction = Direction(code=code, name=name, description=description, is_active=True)
    db.add(direction)
    db.commit()
    return RedirectResponse(url="/info/directions", status_code=303)

@app.post("/info/directions/edit/{direction_id}")
async def info_directions_edit(
    direction_id: int,
    code: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    direction = db.query(Direction).filter(Direction.id == direction_id).first()
    if not direction:
        raise HTTPException(status_code=404, detail="Yo'nalish topilmadi")
    
    existing = db.query(Direction).filter(Direction.code == code, Direction.id != direction_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{code}' kodli yo'nalish allaqachon mavjud!")
    
    direction.code = code
    direction.name = name
    direction.description = description
    db.commit()
    return RedirectResponse(url="/info/directions", status_code=303)

@app.post("/info/directions/delete/{direction_id}")
async def info_directions_delete(direction_id: int, db: Session = Depends(get_db)):
    direction = db.query(Direction).filter(Direction.id == direction_id).first()
    if not direction:
        raise HTTPException(status_code=404, detail="Yo'nalish topilmadi")
    
    db.delete(direction)
    db.commit()
    return RedirectResponse(url="/info/directions", status_code=303)

# --- DIRECTIONS EXCEL OPERATIONS ---
@app.get("/info/directions/export")
async def export_directions(db: Session = Depends(get_db)):
    directions = db.query(Direction).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Directions"
    ws.append(["ID", "Kod", "Nomi", "Izoh"])
    for d in directions:
        ws.append([d.id, d.code, d.name, d.description])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=yonalishlar.xlsx"})

@app.get("/info/directions/template")
async def template_directions():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"
    ws.append(["Kod", "Nomi", "Izoh"])
    ws.append(["DIR001", "Halva", "Halva mahsulotlari"])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=yonalish_andoza.xlsx"})

@app.post("/info/directions/import")
async def import_directions(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(contents))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for row in rows:
        if not row[0]: continue
        code, name, description = row[0], row[1], row[2]
        direction = db.query(Direction).filter(Direction.code == code).first()
        if not direction:
            direction = Direction(code=code, name=name, description=description)
            db.add(direction)
        else:
            direction.name = name
            direction.description = description
        db.commit()
    return RedirectResponse(url="/info/directions", status_code=303)

# Foydalanuvchilar bo'limi
@app.get("/info/users", response_class=HTMLResponse)
async def info_users(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Foydalanuvchilar ro'yxati"""
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    
    users = db.query(User).all()
    return templates.TemplateResponse("info/users.html", {
        "request": request,
        "users": users,
        "current_user": current_user,
        "page_title": "Foydalanuvchilar"
    })

@app.post("/info/users/add")
async def info_users_add(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    role: str = Form("user"),
    is_active: bool = Form(True),
    db: Session = Depends(get_db)
):
    """Yangi foydalanuvchi qo'shish"""
    # Username dublikat tekshiruvi
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{username}' login bilan foydalanuvchi allaqachon mavjud!")
    
    # Yangi foydalanuvchi yaratish
    user = User(
        username=username,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        is_active=is_active
    )
    db.add(user)
    db.commit()
    return RedirectResponse(url="/info/users", status_code=303)

@app.post("/info/users/edit/{user_id}")
async def info_users_edit(
    user_id: int,
    username: str = Form(...),
    full_name: str = Form(...),
    role: str = Form("user"),
    is_active: bool = Form(True),
    db: Session = Depends(get_db)
):
    """Foydalanuvchini tahrirlash"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    # Username dublikat tekshiruvi (o'zidan boshqa)
    existing = db.query(User).filter(
        User.username == username,
        User.id != user_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"'{username}' login bilan foydalanuvchi allaqachon mavjud!")
    
    user.username = username
    user.full_name = full_name
    user.role = role
    user.is_active = is_active
    db.commit()
    return RedirectResponse(url="/info/users", status_code=303)

@app.post("/info/users/change-password/{user_id}")
async def info_users_change_password(
    user_id: int,
    new_password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Foydalanuvchi parolini o'zgartirish"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    user.password_hash = hash_password(new_password)
    db.commit()
    return RedirectResponse(url="/info/users", status_code=303)

@app.post("/info/users/delete/{user_id}")
async def info_users_delete(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Foydalanuvchini o'chirish"""
    # O'zini o'chirishga ruxsat bermaslik
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="O'zingizni o'chira olmaysiz!")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    
    db.delete(user)
    db.commit()
    return RedirectResponse(url="/info/users", status_code=303)

# --- MAHSULOT DETAIL VA BARCODE ---



@app.get("/products/barcode/{product_id}")
async def product_barcode(product_id: int, download: int = 0, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or not product.barcode:
        return HTMLResponse("<h3>Shtixkod topilmadi</h3>", status_code=404)
    # Barcode rasm faylini yaratish
    barcode_path = f"app/static/images/products/barcode_{product.id}.png"
    if not os.path.exists(barcode_path):
        code128 = barcode.get('code128', product.barcode, writer=ImageWriter())
        code128.save(barcode_path[:-4])
    if download:
        return FileResponse(barcode_path, media_type="image/png", filename=f"barcode_{product.code}.png")
    return FileResponse(barcode_path, media_type="image/png")




# ==========================================
# TOVARLAR
# ==========================================
from fastapi import UploadFile, File
from fastapi.responses import StreamingResponse
import io
import openpyxl

# --- EXPORT PRODUCTS TO EXCEL ---
@app.get("/products/export")
async def export_products(db: Session = Depends(get_db)):
    products = db.query(Product).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Products"
    ws.append(["ID", "Kod", "Nomi", "Turi", "Kategoriya", "O'lchov", "Sotish narxi", "Olish narxi"])
    for p in products:
        ws.append([
            p.id, p.code, p.name, p.type,
            p.category.name if p.category else "",
            p.unit.name if p.unit else "",
            p.sale_price, p.purchase_price
        ])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=products.xlsx"})

# --- DOWNLOAD IMPORT TEMPLATE ---
@app.get("/products/template")
async def product_import_template():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Import Template"
    
    # Headers
    headers = ["ID", "Kod", "Nomi", "Turi", "Kategoriya", "O'lchov", "Sotish narxi", "Olish narxi"]
    ws.append(headers)
    
    # Example Row
    example = ["", "P001", "Misol Mahsulot", "tayyor", "Shirinliklar", "dona", 15000, 10000]
    ws.append(example)
    
    # Column width adjustment
    for col in range(1, 9):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 15
    ws.column_dimensions['C'].width = 30  # Name column
    
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=tovar_andoza.xlsx"})

@app.get("/products/{product_id}", response_class=HTMLResponse)
async def product_detail(request: Request, product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return HTMLResponse("<h3>Mahsulot topilmadi</h3>", status_code=404)
    return templates.TemplateResponse("products/detail.html", {"request": request, "product": product})

# --- IMPORT PRODUCTS FROM EXCEL ---
@app.post("/products/import")
async def import_products(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(contents))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for row in rows:
        code, name, type_, category_name, unit_name, sale_price, purchase_price = row[1:8]
        # Kategoriya va o'lchov birligini topish yoki yaratish
        category = db.query(Category).filter(Category.name == category_name).first()
        if not category and category_name:
            category = Category(name=category_name, code=category_name.lower(), type="product")
            db.add(category)
            db.commit()
        unit = db.query(Unit).filter(Unit.name == unit_name).first()
        if not unit and unit_name:
            unit = Unit(name=unit_name, code=unit_name.lower())
            db.add(unit)
            db.commit()
        # Mahsulotni qo'shish yoki yangilash
        product = db.query(Product).filter(Product.code == code).first()
        if not product:
            product = Product(code=code)
            db.add(product)
        product.name = name
        product.type = type_
        product.category_id = category.id if category else None
        product.unit_id = unit.id if unit else None
        product.sale_price = sale_price or 0
        product.purchase_price = purchase_price or 0
        db.commit()
    return RedirectResponse(url="/products", status_code=303)

@app.get("/products", response_class=HTMLResponse)
async def products_list(request: Request, type: str = "all", db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Tovarlar ro'yxati"""
    query = db.query(Product)
    if type == "tayyor":
        query = query.filter(Product.type == "tayyor")
    elif type == "yarim_tayyor":
        query = query.filter(Product.type == "yarim_tayyor")
    elif type == "hom_ashyo":
        query = query.filter(Product.type == "hom_ashyo")
    
    products = query.all()
    categories = db.query(Category).all()
    units = db.query(Unit).all()
    
    return templates.TemplateResponse("products/list.html", {
        "request": request,
        "products": products,
        "categories": categories,
        "units": units,
        "current_type": type,
        "current_user": current_user,
        "page_title": "Tovarlar"
    })



@app.post("/products/add")
async def product_add(
    request: Request,
    name: str = Form(...),
    type: str = Form(...),
    category_id: int = Form(None),
    unit_id: int = Form(None),
    barcode: str = Form(None),
    sale_price: float = Form(0),
    purchase_price: float = Form(0),
    db: Session = Depends(get_db)
):
    """Tovar qo'shish"""
    product = Product(
        name=name,
        code=None,
        type=type,
        category_id=category_id if category_id and category_id > 0 else None,
        unit_id=unit_id if unit_id and unit_id > 0 else None,
        barcode=barcode,
        sale_price=sale_price,
        purchase_price=purchase_price,
        image=None
    )
    db.add(product)
    db.commit()
    
    # Kod generatsiya
    product.code = f"P{product.id:05d}"
    db.commit()
    
    return RedirectResponse(url="/products", status_code=303)


@app.post("/products/{product_id}/upload-image")
async def product_upload_image(
    product_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Mahsulot rasmini yuklash"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
    
    if image and image.filename:
        import shutil, os
        ext = image.filename.split('.')[-1]
        image_filename = f"{product.code}.{ext}"
        image_path = os.path.join("app/static/images/products", image_filename)
        
        # Papkani yaratish
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        
        with open(image_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        
        product.image = image_filename
        db.commit()
    
    return RedirectResponse(url="/products", status_code=303)


# ==========================================
# OMBOR
# ==========================================

@app.get("/warehouse", response_class=HTMLResponse)
async def warehouse_list(request: Request, db: Session = Depends(get_db)):
    """Ombor qoldiqlari"""
    warehouses = db.query(Warehouse).all()
    
    # Qoldiqlar
    stocks = db.query(Stock).join(Product).join(Warehouse).all()
    
    return templates.TemplateResponse("warehouse/list.html", {
        "request": request,
        "warehouses": warehouses,
        "stocks": stocks,
        "page_title": "Ombor"
    })


@app.get("/warehouse/movement", response_class=HTMLResponse)
async def warehouse_movement(request: Request, db: Session = Depends(get_db)):
    """Ombor harakatlari"""
    products = db.query(Product).all()
    warehouses = db.query(Warehouse).all()
    
    return templates.TemplateResponse("warehouse/movement.html", {
        "request": request,
        "products": products,
        "warehouses": warehouses,
        "page_title": "Ombor harakati"
    })


# ==========================================
# TOVAR KIRIMI (PURCHASE)
# ==========================================

@app.get("/purchases", response_class=HTMLResponse)
async def purchases_list(request: Request, db: Session = Depends(get_db)):
    """Tovar kirimlari ro'yxati"""
    purchases = db.query(Purchase).order_by(Purchase.date.desc()).limit(100).all()
    
    return templates.TemplateResponse("purchases/list.html", {
        "request": request,
        "purchases": purchases,
        "page_title": "Tovar kirimlari"
    })


@app.get("/purchases/new", response_class=HTMLResponse)
async def purchase_new(request: Request, db: Session = Depends(get_db)):
    """Yangi tovar kirimi"""
    products = db.query(Product).filter(Product.is_active == True).all()
    partners = db.query(Partner).filter(Partner.type.in_(["supplier", "both"])).all()
    warehouses = db.query(Warehouse).all()
    
    return templates.TemplateResponse("purchases/new.html", {
        "request": request,
        "products": products,
        "partners": partners,
        "warehouses": warehouses,
        "page_title": "Yangi tovar kirimi"
    })


@app.post("/purchases/create")
async def purchase_create(
    request: Request,
    partner_id: int = Form(...),
    warehouse_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Tovar kirimini yaratish"""
    today = datetime.now()
    count = db.query(Purchase).filter(
        Purchase.date >= today.replace(hour=0, minute=0, second=0)
    ).count()
    number = f"P-{today.strftime('%Y%m%d')}-{str(count + 1).zfill(4)}"
    
    purchase = Purchase(
        number=number,
        partner_id=partner_id,
        warehouse_id=warehouse_id,
        status="draft"
    )
    db.add(purchase)
    db.commit()
    
    return RedirectResponse(url=f"/purchases/edit/{purchase.id}", status_code=303)


@app.get("/purchases/edit/{purchase_id}", response_class=HTMLResponse)
async def purchase_edit(request: Request, purchase_id: int, db: Session = Depends(get_db)):
    """Tovar kirimini tahrirlash"""
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Tovar kirimi topilmadi")
    
    products = db.query(Product).filter(Product.is_active == True).all()
    
    return templates.TemplateResponse("purchases/edit.html", {
        "request": request,
        "purchase": purchase,
        "products": products,
        "page_title": f"Tovar kirimi: {purchase.number}"
    })


@app.post("/purchases/{purchase_id}/add-item")
async def purchase_add_item(
    purchase_id: int,
    product_id: int = Form(...),
    quantity: float = Form(...),
    price: float = Form(...),
    db: Session = Depends(get_db)
):
    """Tovar kirimiga mahsulot qo'shish"""
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Tovar kirimi topilmadi")
    
    total = quantity * price
    item = PurchaseItem(
        purchase_id=purchase_id,
        product_id=product_id,
        quantity=quantity,
        price=price,
        total=total
    )
    db.add(item)
    
    purchase.total = db.query(PurchaseItem).filter(
        PurchaseItem.purchase_id == purchase_id
    ).with_entities(db.func.sum(PurchaseItem.total)).scalar() or 0
    purchase.total += total
    
    db.commit()
    return RedirectResponse(url=f"/purchases/edit/{purchase_id}", status_code=303)


@app.post("/purchases/{purchase_id}/confirm")
async def purchase_confirm(purchase_id: int, db: Session = Depends(get_db)):
    """Tovar kirimini tasdiqlash va ombor qoldiqlarini yangilash"""
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Tovar kirimi topilmadi")
    
    if purchase.status != "draft":
        raise HTTPException(status_code=400, detail="Faqat qoralama holatidagi kirimlarni tasdiqlash mumkin")
    
    for item in purchase.items:
        stock = db.query(Stock).filter(
            Stock.warehouse_id == purchase.warehouse_id,
            Stock.product_id == item.product_id
        ).first()
        
        if stock:
            stock.quantity += item.quantity
        else:
            stock = Stock(
                warehouse_id=purchase.warehouse_id,
                product_id=item.product_id,
                quantity=item.quantity
            )
            db.add(stock)
        
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if product:
            product.purchase_price = item.price
    
    purchase.status = "confirmed"
    
    if purchase.partner_id:
        partner = db.query(Partner).filter(Partner.id == purchase.partner_id).first()
        if partner:
            partner.balance -= purchase.total
    
    db.commit()
    return RedirectResponse(url=f"/purchases", status_code=303)


# ==========================================
# MIJOZLAR
# ==========================================

@app.get("/partners", response_class=HTMLResponse)
async def partners_list(request: Request, type: str = "all", db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Kontragentlar ro'yxati"""
    query = db.query(Partner)
    if type != "all":
        query = query.filter(Partner.type == type)
    
    partners = query.all()
    
    return templates.TemplateResponse("partners/list.html", {
        "request": request,
        "partners": partners,
        "current_type": type,
        "current_user": current_user,
        "page_title": "Kontragentlar"
    })


@app.post("/partners/add")
async def partner_add(
    request: Request,
    name: str = Form(...),
    type: str = Form(...),
    phone: str = Form(""),
    address: str = Form(""),
    credit_limit: float = Form(0),
    discount_percent: float = Form(0),
    db: Session = Depends(get_db)
):
    """Kontragent qo'shish"""
    # Dublikat tekshiruvi - nom bo'yicha
    existing_by_name = db.query(Partner).filter(Partner.name == name).first()
    if existing_by_name:
        raise HTTPException(status_code=400, detail=f"'{name}' nomli kontragent allaqachon mavjud!")
    
    # Dublikat tekshiruvi - telefon bo'yicha (agar telefon kiritilgan bo'lsa)
    if phone and phone.strip():
        existing_by_phone = db.query(Partner).filter(Partner.phone == phone).first()
        if existing_by_phone:
            raise HTTPException(status_code=400, detail=f"'{phone}' telefon raqamli kontragent allaqachon mavjud!")
    
    partner = Partner(
        name=name,
        code=None,  # Kod kerak emas
        type=type,
        phone=phone,
        address=address,
        credit_limit=credit_limit,
        discount_percent=discount_percent
    )
    db.add(partner)
    db.commit()
    return RedirectResponse(url="/partners", status_code=303)


@app.post("/partners/edit/{partner_id}")
async def partner_edit(
    partner_id: int,
    name: str = Form(...),
    type: str = Form(...),
    phone: str = Form(""),
    address: str = Form(""),
    credit_limit: float = Form(0),
    discount_percent: float = Form(0),
    db: Session = Depends(get_db)
):
    """Kontragentni tahrirlash"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Kontragent topilmadi")
    
    # Dublikat tekshiruvi - nom bo'yicha (o'zidan boshqa)
    existing_by_name = db.query(Partner).filter(
        Partner.name == name,
        Partner.id != partner_id
    ).first()
    if existing_by_name:
        raise HTTPException(status_code=400, detail=f"'{name}' nomli kontragent allaqachon mavjud!")
    
    # Dublikat tekshiruvi - telefon bo'yicha (agar telefon kiritilgan bo'lsa va o'zidan boshqa)
    if phone and phone.strip():
        existing_by_phone = db.query(Partner).filter(
            Partner.phone == phone,
            Partner.id != partner_id
        ).first()
        if existing_by_phone:
            raise HTTPException(status_code=400, detail=f"'{phone}' telefon raqamli kontragent allaqachon mavjud!")
    
    partner.name = name
    # partner.code o'zgartirilmaydi - avtomatik generatsiya qilingan
    partner.type = type
    partner.phone = phone
    partner.address = address
    partner.credit_limit = credit_limit
    partner.discount_percent = discount_percent
    
    db.commit()
    return RedirectResponse(url="/partners", status_code=303)


@app.post("/partners/delete/{partner_id}")
async def partner_delete(partner_id: int, db: Session = Depends(get_db)):
    """Kontragentni o'chirish"""
    partner = db.query(Partner).filter(Partner.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="Kontragent topilmadi")
    
    # Kontragent bilan bog'liq buyurtmalar borligini tekshirish
    has_orders = db.query(Order).filter(Order.partner_id == partner_id).first()
    has_purchases = db.query(Purchase).filter(Purchase.partner_id == partner_id).first()
    
    if has_orders or has_purchases:
        raise HTTPException(
            status_code=400, 
            detail="Bu kontragent bilan bog'liq buyurtmalar yoki kirimlar mavjud. O'chirish mumkin emas."
        )
    
    db.delete(partner)
    db.commit()
    return RedirectResponse(url="/partners", status_code=303)


# --- PARTNERS EXCEL OPERATIONS ---
@app.get("/partners/export")
async def export_partners(db: Session = Depends(get_db)):
    partners = db.query(Partner).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Partners"
    ws.append(["ID", "Kod", "Nomi", "Turi", "Telefon", "Manzil", "Kredit Limit", "Chegirma %"])
    for p in partners:
        ws.append([p.id, p.code, p.name, p.type, p.phone, p.address, p.credit_limit, p.discount_percent])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=kontragentlar.xlsx"})

@app.get("/partners/template")
async def template_partners():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"
    ws.append(["Nomi", "Turi", "Telefon", "Manzil", "Kredit Limit", "Chegirma %"])
    ws.append(["Mijoz MCHJ", "customer", "+998901234567", "Toshkent", 1000000, 0])
    ws.append(["Yetkazib Beruvchi", "supplier", "+998909876543", "Samarqand", 0, 0])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=kontragent_andoza.xlsx"})

@app.post("/partners/import")
async def import_partners(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(contents))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for row in rows:
        if not row[0]: continue
        name, type_, phone, address, credit_limit, discount_percent = row[0:6]
        partner = db.query(Partner).filter(Partner.name == name).first()
        if not partner:
            # Kod generatsiya
            count = db.query(Partner).count()
            code = f"P{count + 1:04d}"
            partner = Partner(
                code=code,
                name=name, 
                type=type_, 
                phone=phone, 
                address=address, 
                credit_limit=credit_limit, 
                discount_percent=discount_percent
            )
            db.add(partner)
        else:
            partner.phone = phone
            partner.address = address
            partner.credit_limit = credit_limit
            partner.discount_percent = discount_percent
        db.commit()
    return RedirectResponse(url="/partners", status_code=303)


# ==========================================
# SAVDO
# ==========================================

@app.get("/sales", response_class=HTMLResponse)
async def sales_list(request: Request, db: Session = Depends(get_db)):
    """Sotuvlar ro'yxati"""
    orders = db.query(Order).filter(Order.type == "sale").order_by(Order.date.desc()).limit(100).all()
    
    return templates.TemplateResponse("sales/list.html", {
        "request": request,
        "orders": orders,
        "page_title": "Sotuvlar"
    })


@app.get("/sales/new", response_class=HTMLResponse)
async def sales_new(request: Request, db: Session = Depends(get_db)):
    """Yangi sotuv"""
    products = db.query(Product).filter(Product.type.in_(["tayyor", "yarim_tayyor"]), Product.is_active == True).all()
    partners = db.query(Partner).filter(Partner.type.in_(["customer", "both"])).all()
    warehouses = db.query(Warehouse).all()
    
    return templates.TemplateResponse("sales/new.html", {
        "request": request,
        "products": products,
        "partners": partners,
        "warehouses": warehouses,
        "page_title": "Yangi sotuv"
    })


@app.post("/sales/create")
async def sales_create(
    request: Request,
    partner_id: int = Form(...),
    warehouse_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Sotuv yaratish"""
    # Yangi raqam generatsiya
    last_order = db.query(Order).filter(Order.type == "sale").order_by(Order.id.desc()).first()
    new_number = f"S-{datetime.now().strftime('%Y%m%d')}-{(last_order.id + 1) if last_order else 1:04d}"
    
    order = Order(
        number=new_number,
        type="sale",
        partner_id=partner_id,
        warehouse_id=warehouse_id,
        status="draft"
    )
    db.add(order)
    db.commit()
    
    return RedirectResponse(url=f"/sales/edit/{order.id}", status_code=303)


# ==========================================
# MOLIYA
# ==========================================

@app.get("/finance", response_class=HTMLResponse)
async def finance(request: Request, db: Session = Depends(get_db)):
    """Moliya - kassa"""
    cash_registers = db.query(CashRegister).all()
    
    # So'nggi to'lovlar
    payments = db.query(Payment).order_by(Payment.date.desc()).limit(50).all()
    
    # Bugungi statistika
    today = datetime.now().date()
    today_income = db.query(Payment).filter(
        Payment.type == "income",
        Payment.date >= today
    ).all()
    today_expense = db.query(Payment).filter(
        Payment.type == "expense",
        Payment.date >= today
    ).all()
    
    stats = {
        "today_income": sum(p.amount for p in today_income),
        "today_expense": sum(p.amount for p in today_expense),
    }
    
    return templates.TemplateResponse("finance/index.html", {
        "request": request,
        "cash_registers": cash_registers,
        "payments": payments,
        "stats": stats,
        "page_title": "Moliya"
    })


# ==========================================
# XODIMLAR
# ==========================================

@app.get("/employees", response_class=HTMLResponse)
async def employees_list(request: Request, db: Session = Depends(get_db), current_user: User = Depends(require_auth)):
    """Xodimlar ro'yxati"""
    employees = db.query(Employee).all()
    
    return templates.TemplateResponse("employees/list.html", {
        "request": request,
        "employees": employees,
        "current_user": current_user,
        "page_title": "Xodimlar"
    })


@app.post("/employees/add")
async def employee_add(
    request: Request,
    full_name: str = Form(...),
    code: str = Form(...),
    position: str = Form(""),
    department: str = Form(""),
    phone: str = Form(""),
    salary: float = Form(0),
    db: Session = Depends(get_db)
):
    """Xodim qo'shish"""
    employee = Employee(
        full_name=full_name,
        code=code,
        position=position,
        department=department,
        phone=phone,
        salary=salary
    )
    db.add(employee)
    db.commit()
    return RedirectResponse(url="/employees", status_code=303)


# --- EMPLOYEES EXCEL OPERATIONS ---
@app.get("/employees/export")
async def export_employees(db: Session = Depends(get_db)):
    employees = db.query(Employee).all()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Employees"
    ws.append(["ID", "Kod", "F.I.SH", "Lavozim", "Bo'lim", "Telefon", "Oylik"])
    for e in employees:
        ws.append([e.id, e.code, e.full_name, e.position, e.department, e.phone, e.salary])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=xodimlar.xlsx"})

@app.get("/employees/template")
async def template_employees():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Template"
    ws.append(["Kod", "F.I.SH", "Lavozim", "Bo'lim", "Telefon", "Oylik"])
    ws.append(["X001", "Aliyev Vali", "Ishchi", "Ishlab chiqarish", "+998901234567", 3000000])
    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=xodim_andoza.xlsx"})

@app.post("/employees/import")
async def import_employees(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    wb = openpyxl.load_workbook(io.BytesIO(contents))
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    for row in rows:
        if not row[0]: continue
        code, full_name, position, department, phone, salary = row[0:6]
        employee = db.query(Employee).filter(Employee.code == code).first()
        if not employee:
            employee = Employee(
                code=code, 
                full_name=full_name, 
                position=position, 
                department=department, 
                phone=phone, 
                salary=salary
            )
            db.add(employee)
        else:
            employee.full_name = full_name
            employee.position = position
            employee.department = department
            employee.phone = phone
            employee.salary = salary
        db.commit()
    return RedirectResponse(url="/employees", status_code=303)


# ==========================================
# HISOBOTLAR
# ==========================================

@app.get("/reports", response_class=HTMLResponse)
async def reports(request: Request):
    """Hisobotlar"""
    return templates.TemplateResponse("reports/index.html", {
        "request": request,
        "page_title": "Hisobotlar"
    })


@app.get("/reports/sales", response_class=HTMLResponse)
async def report_sales(
    request: Request,
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db)
):
    """Savdo hisoboti"""
    if not start_date:
        start_date = datetime.now().replace(day=1).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    orders = db.query(Order).filter(
        Order.type == "sale",
        Order.date >= start_date,
        Order.date <= end_date + " 23:59:59"
    ).all()
    
    total = sum(o.total for o in orders)
    
    return templates.TemplateResponse("reports/sales.html", {
        "request": request,
        "orders": orders,
        "total": total,
        "start_date": start_date,
        "end_date": end_date,
        "page_title": "Savdo hisoboti"
    })


@app.get("/reports/stock", response_class=HTMLResponse)
async def report_stock(request: Request, db: Session = Depends(get_db)):
    """Qoldiq hisoboti"""
    stocks = db.query(Stock).join(Product).all()
    
    return templates.TemplateResponse("reports/stock.html", {
        "request": request,
        "stocks": stocks,
        "page_title": "Qoldiq hisoboti"
    })


@app.get("/reports/debts", response_class=HTMLResponse)
async def report_debts(request: Request, db: Session = Depends(get_db)):
    """Qarzdorlik hisoboti"""
    debtors = db.query(Partner).filter(Partner.balance != 0).all()
    
    total_debt = sum(p.balance for p in debtors if p.balance > 0)
    total_credit = sum(abs(p.balance) for p in debtors if p.balance < 0)
    
    return templates.TemplateResponse("reports/debts.html", {
        "request": request,
        "debtors": debtors,
        "total_debt": total_debt,
        "total_credit": total_credit,
        "page_title": "Qarzdorlik hisoboti"
    })


# ==========================================
# ISHLAB CHIQARISH
# ==========================================

@app.get("/production", response_class=HTMLResponse)
async def production_dashboard(request: Request, db: Session = Depends(get_db)):
    """Ishlab chiqarish bosh sahifasi"""
    today = datetime.now().date()
    
    # Statistika
    total_recipes = db.query(Recipe).filter(Recipe.is_active == True).count()
    today_productions = db.query(Production).filter(
        Production.date >= today,
        Production.status == "completed"
    ).all()
    today_quantity = sum(p.quantity for p in today_productions)
    
    pending_productions = db.query(Production).filter(
        Production.status == "draft"
    ).count()
    
    # Oxirgi ishlab chiqarishlar
    recent_productions = db.query(Production).order_by(
        Production.date.desc()
    ).limit(10).all()
    
    # Retseptlar
    recipes = db.query(Recipe).filter(Recipe.is_active == True).all()
    
    return templates.TemplateResponse("production/index.html", {
        "request": request,
        "total_recipes": total_recipes,
        "today_quantity": today_quantity,
        "pending_productions": pending_productions,
        "recent_productions": recent_productions,
        "recipes": recipes,
        "page_title": "Ishlab chiqarish"
    })


@app.get("/production/recipes", response_class=HTMLResponse)
async def production_recipes(request: Request, db: Session = Depends(get_db)):
    """Retseptlar ro'yxati"""
    recipes = db.query(Recipe).all()
    products = db.query(Product).filter(Product.type.in_(["tayyor", "yarim_tayyor"])).all()
    materials = db.query(Product).filter(Product.type == "hom_ashyo").all()
    
    return templates.TemplateResponse("production/recipes.html", {
        "request": request,
        "recipes": recipes,
        "products": products,
        "materials": materials,
        "page_title": "Retseptlar"
    })


@app.get("/production/recipes/{recipe_id}", response_class=HTMLResponse)
async def production_recipe_detail(request: Request, recipe_id: int, db: Session = Depends(get_db)):
    """Retsept tafsilotlari"""
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(status_code=404, detail="Retsept topilmadi")
    
    materials = db.query(Product).filter(Product.type.in_(["hom_ashyo", "yarim_tayyor", "tayyor"])).all()
    
    return templates.TemplateResponse("production/recipe_detail.html", {
        "request": request,
        "recipe": recipe,
        "materials": materials,
        "page_title": f"Retsept: {recipe.name}"
    })


@app.post("/production/recipes/add")
async def add_recipe(
    request: Request,
    name: str = Form(...),
    product_id: int = Form(...),
    output_quantity: float = Form(1),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    """Yangi retsept qo'shish"""
    recipe = Recipe(
        name=name,
        product_id=product_id,
        output_quantity=output_quantity,
        description=description,
        is_active=True
    )
    db.add(recipe)
    db.commit()
    return RedirectResponse(url=f"/production/recipes/{recipe.id}", status_code=303)


@app.post("/production/recipes/{recipe_id}/add-item")
async def add_recipe_item(
    recipe_id: int,
    product_id: int = Form(...),
    quantity: float = Form(...),
    db: Session = Depends(get_db)
):
    """Retseptga xom ashyo qo'shish"""
    item = RecipeItem(
        recipe_id=recipe_id,
        product_id=product_id,
        quantity=quantity
    )
    db.add(item)
    db.commit()
    return RedirectResponse(url=f"/production/recipes/{recipe_id}", status_code=303)


@app.get("/production/orders", response_class=HTMLResponse)
async def production_orders(request: Request, db: Session = Depends(get_db)):
    """Ishlab chiqarish buyurtmalari"""
    productions = db.query(Production).order_by(Production.date.desc()).all()
    
    return templates.TemplateResponse("production/orders.html", {
        "request": request,
        "productions": productions,
        "page_title": "Ishlab chiqarish buyurtmalari"
    })


@app.get("/production/new", response_class=HTMLResponse)
async def production_new(request: Request, db: Session = Depends(get_db)):
    """Yangi ishlab chiqarish"""
    recipes = db.query(Recipe).filter(Recipe.is_active == True).all()
    warehouses = db.query(Warehouse).all()
    
    return templates.TemplateResponse("production/new_order.html", {
        "request": request,
        "recipes": recipes,
        "warehouses": warehouses,
        "page_title": "Yangi ishlab chiqarish"
    })



from typing import List

@app.post("/production/create")
async def create_production(
    request: Request,
    recipe_id: int = Form(...),
    warehouse_id: int = Form(...),
    quantity: float = Form(...),
    note: str = Form(""),
    material_product_id: List[int] = Form([]),
    material_quantity: List[float] = Form([]),
    db: Session = Depends(get_db)
):
    """Ishlab chiqarish yaratish (tarkibni qo'lda o'zgartirish bilan)"""
    today = datetime.now()
    count = db.query(Production).filter(
        Production.date >= today.replace(hour=0, minute=0, second=0)
    ).count()
    number = f"PR-{today.strftime('%Y%m%d')}-{str(count + 1).zfill(3)}"

    production = Production(
        number=number,
        recipe_id=recipe_id,
        warehouse_id=warehouse_id,
        quantity=quantity,
        note=note,
        status="draft"
    )
    db.add(production)
    db.flush()  # production.id olish uchun

    # Foydalanuvchi o'zgartirgan tarkibni saqlash (Production tarkibi sifatida)
    # (Agar kerak bo'lsa, alohida ProductionMaterial model qilish mumkin, hozircha RecipeItem orqali)
    for pid, qty in zip(material_product_id, material_quantity):
        if pid and qty:
            db.add(RecipeItem(recipe_id=production.id, product_id=pid, quantity=qty))

    db.commit()
    return RedirectResponse(url="/production/orders", status_code=303)


@app.post("/production/{prod_id}/complete")
async def complete_production(prod_id: int, db: Session = Depends(get_db)):
    """Ishlab chiqarishni yakunlash"""
    production = db.query(Production).filter(Production.id == prod_id).first()
    if not production:
        raise HTTPException(status_code=404, detail="Topilmadi")
    
    recipe = db.query(Recipe).filter(Recipe.id == production.recipe_id).first()
    
    # Xom ashyolarni ayirish
    for item in recipe.items:
        stock = db.query(Stock).filter(
            Stock.warehouse_id == production.warehouse_id,
            Stock.product_id == item.product_id
        ).first()
        if stock:
            stock.quantity -= item.quantity * production.quantity
    
    # Tayyor mahsulotni qo'shish
    product_stock = db.query(Stock).filter(
        Stock.warehouse_id == production.warehouse_id,
        Stock.product_id == recipe.product_id
    ).first()
    
    if product_stock:
        product_stock.quantity += production.quantity * recipe.output_quantity
    else:
        new_stock = Stock(
            warehouse_id=production.warehouse_id,
            product_id=recipe.product_id,
            quantity=production.quantity * recipe.output_quantity
        )
        db.add(new_stock)
    
    production.status = "completed"
    db.commit()
    return RedirectResponse(url="/production/orders", status_code=303)


@app.post("/production/{prod_id}/cancel")
async def cancel_production(prod_id: int, db: Session = Depends(get_db)):
    """Ishlab chiqarishni bekor qilish"""
    production = db.query(Production).filter(Production.id == prod_id).first()
    if not production:
        raise HTTPException(status_code=404, detail="Topilmadi")
    
    production.status = "cancelled"
    db.commit()
    return RedirectResponse(url="/production/orders", status_code=303)


# ==========================================
# API (Telegram bot uchun)
# ==========================================

@app.get("/api/stats")
async def api_stats(db: Session = Depends(get_db)):
    """Statistika API"""
    today = datetime.now().date()
    
    today_sales = db.query(Order).filter(
        Order.type == "sale",
        Order.date >= today
    ).all()
    
    cash = db.query(CashRegister).first()
    
    return {
        "today_sales": sum(o.total for o in today_sales),
        "today_orders": len(today_sales),
        "cash_balance": cash.balance if cash else 0,
        "products_count": db.query(Product).count(),
        "partners_count": db.query(Partner).count(),
    }


@app.get("/api/products")
async def api_products(db: Session = Depends(get_db)):
    """Tovarlar API"""
    products = db.query(Product).filter(Product.is_active == True).all()
    return [{"id": p.id, "name": p.name, "code": p.code, "price": p.sale_price} for p in products]


@app.get("/api/partners")
async def api_partners(db: Session = Depends(get_db)):
    """Kontragentlar API"""
    partners = db.query(Partner).filter(Partner.is_active == True).all()
    return [{"id": p.id, "name": p.name, "balance": p.balance} for p in partners]


# ==========================================
# AGENTLAR
# ==========================================

@app.get("/agents", response_class=HTMLResponse)
async def agents_list(request: Request, db: Session = Depends(get_db)):
    """Agentlar ro'yxati"""
    agents = db.query(Agent).all()
    
    # Har bir agent uchun oxirgi lokatsiya
    for agent in agents:
        last_loc = db.query(AgentLocation).filter(
            AgentLocation.agent_id == agent.id
        ).order_by(AgentLocation.recorded_at.desc()).first()
        agent.last_location = last_loc
        
        # Bugungi tashriflar
        today = datetime.now().date()
        agent.today_visits = db.query(Visit).filter(
            Visit.agent_id == agent.id,
            Visit.visit_date >= today
        ).count()
    
    return templates.TemplateResponse("agents/list.html", {
        "request": request,
        "agents": agents,
        "page_title": "Agentlar"
    })


@app.post("/agents/add")
async def agent_add(
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(""),
    region: str = Form(""),
    telegram_id: str = Form(""),
    db: Session = Depends(get_db)
):
    """Agent qo'shish"""
    agent = Agent(
        full_name=full_name,
        phone=phone,
        region=region,
        telegram_id=telegram_id
    )
    db.add(agent)
    db.commit()
    return RedirectResponse(url="/agents", status_code=303)


@app.get("/agents/{agent_id}", response_class=HTMLResponse)
async def agent_detail(request: Request, agent_id: int, db: Session = Depends(get_db)):
    """Agent tafsilotlari"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent topilmadi")
    
    # Oxirgi lokatsiyalar
    locations = db.query(AgentLocation).filter(
        AgentLocation.agent_id == agent_id
    ).order_by(AgentLocation.recorded_at.desc()).limit(50).all()
    
    # Tashriflar
    visits = db.query(Visit).filter(
        Visit.agent_id == agent_id
    ).order_by(Visit.visit_date.desc()).limit(30).all()
    
    return templates.TemplateResponse("agents/detail.html", {
        "request": request,
        "agent": agent,
        "locations": locations,
        "visits": visits,
        "page_title": f"Agent: {agent.full_name}"
    })


# ==========================================
# YETKAZIB BERISH
# ==========================================

@app.get("/delivery", response_class=HTMLResponse)
async def delivery_list(request: Request, db: Session = Depends(get_db)):
    """Yetkazib berish ro'yxati"""
    drivers = db.query(Driver).all()
    
    # Har bir haydovchi uchun statistika
    for driver in drivers:
        last_loc = db.query(DriverLocation).filter(
            DriverLocation.driver_id == driver.id
        ).order_by(DriverLocation.recorded_at.desc()).first()
        driver.last_location = last_loc
        
        # Bugungi yetkazilganlar
        today = datetime.now().date()
        driver.today_deliveries = db.query(Delivery).filter(
            Delivery.driver_id == driver.id,
            Delivery.created_at >= today
        ).count()
        
        driver.pending_deliveries = db.query(Delivery).filter(
            Delivery.driver_id == driver.id,
            Delivery.status == "pending"
        ).count()
    
    # Barcha yetkazishlar
    deliveries = db.query(Delivery).order_by(Delivery.created_at.desc()).limit(50).all()
    
    return templates.TemplateResponse("delivery/list.html", {
        "request": request,
        "drivers": drivers,
        "deliveries": deliveries,
        "page_title": "Yetkazib berish"
    })


@app.post("/drivers/add")
async def driver_add(
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(""),
    vehicle_number: str = Form(""),
    vehicle_type: str = Form(""),
    telegram_id: str = Form(""),
    db: Session = Depends(get_db)
):
    """Haydovchi qo'shish"""
    driver = Driver(
        full_name=full_name,
        phone=phone,
        vehicle_number=vehicle_number,
        vehicle_type=vehicle_type,
        telegram_id=telegram_id
    )
    db.add(driver)
    db.commit()
    return RedirectResponse(url="/delivery", status_code=303)


@app.get("/delivery/{driver_id}", response_class=HTMLResponse)
async def driver_detail(request: Request, driver_id: int, db: Session = Depends(get_db)):
    """Haydovchi tafsilotlari"""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Haydovchi topilmadi")
    
    # Lokatsiya tarixi
    locations = db.query(DriverLocation).filter(
        DriverLocation.driver_id == driver_id
    ).order_by(DriverLocation.recorded_at.desc()).limit(100).all()
    
    # Yetkazishlar
    deliveries = db.query(Delivery).filter(
        Delivery.driver_id == driver_id
    ).order_by(Delivery.created_at.desc()).limit(30).all()
    
    return templates.TemplateResponse("delivery/detail.html", {
        "request": request,
        "driver": driver,
        "locations": locations,
        "deliveries": deliveries,
        "page_title": f"Haydovchi: {driver.full_name}"
    })


# ==========================================
# XARITA
# ==========================================

@app.get("/map", response_class=HTMLResponse)
async def map_view(request: Request, db: Session = Depends(get_db)):
    """Xarita - barcha joylashuvlar"""
    
    # Agentlar
    agents = db.query(Agent).filter(Agent.is_active == True).all()
    agent_markers = []
    for agent in agents:
        last_loc = db.query(AgentLocation).filter(
            AgentLocation.agent_id == agent.id
        ).order_by(AgentLocation.recorded_at.desc()).first()
        if last_loc:
            agent_markers.append({
                "id": agent.id,
                "name": agent.full_name,
                "type": "agent",
                "lat": last_loc.latitude,
                "lng": last_loc.longitude,
                "time": last_loc.recorded_at.strftime("%H:%M")
            })
    
    # Haydovchilar
    drivers = db.query(Driver).filter(Driver.is_active == True).all()
    driver_markers = []
    for driver in drivers:
        last_loc = db.query(DriverLocation).filter(
            DriverLocation.driver_id == driver.id
        ).order_by(DriverLocation.recorded_at.desc()).first()
        if last_loc:
            driver_markers.append({
                "id": driver.id,
                "name": driver.full_name,
                "type": "driver",
                "lat": last_loc.latitude,
                "lng": last_loc.longitude,
                "time": last_loc.recorded_at.strftime("%H:%M"),
                "vehicle": driver.vehicle_number
            })
    
    # Mijozlar
    partners = db.query(Partner).filter(Partner.is_active == True).all()
    partner_locations = db.query(PartnerLocation).all()
    partner_markers = []
    for loc in partner_locations:
        partner = db.query(Partner).filter(Partner.id == loc.partner_id).first()
        if partner and loc.latitude and loc.longitude:
            partner_markers.append({
                "id": loc.partner_id,
                "name": partner.name,
                "type": "partner",
                "lat": loc.latitude,
                "lng": loc.longitude,
                "address": loc.address
            })
    
    return templates.TemplateResponse("map/index.html", {
        "request": request,
        "agents": agents,
        "drivers": drivers,
        "partner_locations": partner_locations,
        "agent_markers": agent_markers,
        "driver_markers": driver_markers,
        "partner_markers": partner_markers,
        "page_title": "Xarita"
    })


# ==========================================
# SUPERVAYZER DASHBOARD
# ==========================================

@app.get("/supervisor", response_class=HTMLResponse)
async def supervisor_dashboard(request: Request, db: Session = Depends(get_db)):
    """Supervayzer dashboard"""
    today = datetime.now().date()
    
    # Agentlar statistikasi
    total_agents = db.query(Agent).filter(Agent.is_active == True).count()
    active_agents = 0
    for agent in db.query(Agent).filter(Agent.is_active == True).all():
        last_loc = db.query(AgentLocation).filter(
            AgentLocation.agent_id == agent.id,
            AgentLocation.recorded_at >= today
        ).first()
        if last_loc:
            active_agents += 1
    
    # Bugungi tashriflar
    today_visits = db.query(Visit).filter(Visit.visit_date >= today).count()
    
    # Bugungi buyurtmalar
    today_orders = db.query(Order).filter(
        Order.type == "sale",
        Order.date >= today
    ).all()
    today_sales_sum = sum(o.total for o in today_orders)
    
    # Yetkazib berish statistikasi
    total_drivers = db.query(Driver).filter(Driver.is_active == True).count()
    pending_deliveries = db.query(Delivery).filter(Delivery.status == "pending").count()
    today_delivered = db.query(Delivery).filter(
        Delivery.status == "delivered",
        Delivery.delivered_at >= today
    ).count()
    
    # Agent reytingi (bugungi savdo bo'yicha)
    agent_stats = []
    for agent in db.query(Agent).filter(Agent.is_active == True).all():
        visits = db.query(Visit).filter(
            Visit.agent_id == agent.id,
            Visit.visit_date >= today
        ).count()
        
        # So'nggi lokatsiya
        last_loc = db.query(AgentLocation).filter(
            AgentLocation.agent_id == agent.id
        ).order_by(AgentLocation.recorded_at.desc()).first()
        
        agent_stats.append({
            "agent": agent,
            "visits": visits,
            "last_seen": last_loc.recorded_at if last_loc else None,
            "is_online": last_loc and (datetime.now() - last_loc.recorded_at).seconds < 600 if last_loc else False
        })
    
    # Eng faol agentlar
    agent_stats.sort(key=lambda x: x["visits"], reverse=True)
    
    stats = {
        "total_agents": total_agents,
        "active_agents": active_agents,
        "today_visits": today_visits,
        "today_orders": len(today_orders),
        "today_sales": today_sales_sum,
        "total_drivers": total_drivers,
        "pending_deliveries": pending_deliveries,
        "today_delivered": today_delivered,
    }
    
    # Barcha agentlar va haydovchilar
    agents = db.query(Agent).filter(Agent.is_active == True).all()
    drivers = db.query(Driver).filter(Driver.is_active == True).all()
    
    # Oxirgi tashriflar va yetkazishlar
    recent_visits = db.query(Visit).order_by(Visit.visit_date.desc()).limit(10).all()
    recent_deliveries = db.query(Delivery).order_by(Delivery.created_at.desc()).limit(10).all()
    
    return templates.TemplateResponse("supervisor/dashboard.html", {
        "request": request,
        "stats": stats,
        "agents": agents,
        "drivers": drivers,
        "agent_stats": agent_stats[:10],
        "recent_visits": recent_visits,
        "recent_deliveries": recent_deliveries,
        "page_title": "Supervayzer",
        "now": datetime.now()
    })


# ==========================================
# POST Routes - Agent va Driver qo'shish
# ==========================================

@app.post("/agents/add")
async def add_agent(
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(None),
    region: str = Form(None),
    telegram_id: str = Form(None),
    db: Session = Depends(get_db)
):
    """Yangi agent qo'shish"""
    # Kod generatsiya
    last_agent = db.query(Agent).order_by(Agent.id.desc()).first()
    code = f"AG{str((last_agent.id if last_agent else 0) + 1).zfill(3)}"
    
    agent = Agent(
        code=code,
        full_name=full_name,
        phone=phone,
        region=region,
        telegram_id=telegram_id,
        is_active=True
    )
    db.add(agent)
    db.commit()
    return RedirectResponse(url="/agents", status_code=303)


@app.post("/delivery/add-driver")
async def add_driver(
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(None),
    vehicle_type: str = Form(None),
    vehicle_number: str = Form(None),
    telegram_id: str = Form(None),
    db: Session = Depends(get_db)
):
    """Yangi haydovchi qo'shish"""
    # Kod generatsiya
    last_driver = db.query(Driver).order_by(Driver.id.desc()).first()
    code = f"DR{str((last_driver.id if last_driver else 0) + 1).zfill(3)}"
    
    driver = Driver(
        code=code,
        full_name=full_name,
        phone=phone,
        vehicle_type=vehicle_type,
        vehicle_number=vehicle_number,
        telegram_id=telegram_id,
        is_active=True
    )
    db.add(driver)
    db.commit()
    return RedirectResponse(url="/delivery", status_code=303)


@app.post("/delivery/add-order")
async def add_delivery_order(
    request: Request,
    driver_id: int = Form(...),
    order_number: str = Form(...),
    delivery_address: str = Form(...),
    notes: str = Form(None),
    db: Session = Depends(get_db)
):
    """Yangi yetkazish buyurtmasi qo'shish"""
    delivery = Delivery(
        driver_id=driver_id,
        order_number=order_number,
        delivery_address=delivery_address,
        notes=notes,
        status="pending"
    )
    db.add(delivery)
    db.commit()
    return RedirectResponse(url=f"/delivery/{driver_id}", status_code=303)


# ==========================================
# GPS API (Mobil ilova uchun)
# ==========================================

@app.post("/api/agent/location")
async def update_agent_location(
    agent_code: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    accuracy: float = Form(0),
    battery: int = Form(100),
    db: Session = Depends(get_db)
):
    """Agent lokatsiyasini yangilash"""
    agent = db.query(Agent).filter(Agent.code == agent_code).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent topilmadi")
    
    location = AgentLocation(
        agent_id=agent.id,
        latitude=latitude,
        longitude=longitude,
        accuracy=accuracy,
        battery=battery
    )
    db.add(location)
    db.commit()
    return {"status": "ok", "message": "Lokatsiya saqlandi"}


@app.post("/api/driver/location")
async def update_driver_location(
    driver_code: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    speed: float = Form(0),
    db: Session = Depends(get_db)
):
    """Haydovchi lokatsiyasini yangilash"""
    driver = db.query(Driver).filter(Driver.code == driver_code).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Haydovchi topilmadi")
    
    location = DriverLocation(
        driver_id=driver.id,
        latitude=latitude,
        longitude=longitude,
        speed=speed
    )
    db.add(location)
    db.commit()
    return {"status": "ok", "message": "Lokatsiya saqlandi"}


@app.get("/api/agents/locations")
async def get_agents_locations(db: Session = Depends(get_db)):
    """Barcha agentlarning oxirgi joylashuvi"""
    agents = db.query(Agent).filter(Agent.is_active == True).all()
    result = []
    for agent in agents:
        last_loc = db.query(AgentLocation).filter(
            AgentLocation.agent_id == agent.id
        ).order_by(AgentLocation.recorded_at.desc()).first()
        if last_loc:
            result.append({
                "id": agent.id,
                "name": agent.full_name,
                "code": agent.code,
                "lat": last_loc.latitude,
                "lng": last_loc.longitude,
                "time": last_loc.recorded_at.isoformat(),
                "battery": last_loc.battery
            })
    return result


@app.get("/api/drivers/locations")
async def get_drivers_locations(db: Session = Depends(get_db)):
    """Barcha haydovchilarning oxirgi joylashuvi"""
    drivers = db.query(Driver).filter(Driver.is_active == True).all()
    result = []
    for driver in drivers:
        last_loc = db.query(DriverLocation).filter(
            DriverLocation.driver_id == driver.id
        ).order_by(DriverLocation.recorded_at.desc()).first()
        if last_loc:
            result.append({
                "id": driver.id,
                "name": driver.full_name,
                "code": driver.code,
                "vehicle": driver.vehicle_number,
                "lat": last_loc.latitude,
                "lng": last_loc.longitude,
                "time": last_loc.recorded_at.isoformat(),
                "speed": last_loc.speed
            })
    return result


# ==========================================
# STARTUP
# ==========================================

@app.on_event("startup")
async def startup():
    """Dastur ishga tushganda"""
    init_db()
    print("рџљЂ TOTLI HOLVA Business System ishga tushdi!")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)

