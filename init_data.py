# ============================================
# TOTLI HOLVA - Boshlang'ich ma'lumotlar
# ============================================

from app.models.database import (
    engine, SessionLocal, Base,
    User, Category, Unit, Warehouse, Product, CashRegister, Partner, Employee,
    Agent, AgentLocation, Driver, DriverLocation, PartnerLocation,
    Recipe, RecipeItem
)
from app.utils.auth import hash_password
from datetime import datetime, timedelta
import random

def init_data():
    """Boshlang'ich ma'lumotlarni qo'shish"""
    
    # Jadvallarni yaratish
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Barcha namunaviy ma'lumotlarni o'chirish
        db.query(RecipeItem).delete()
        db.query(Recipe).delete()
        db.query(PartnerLocation).delete()
        db.query(DriverLocation).delete()
        db.query(Driver).delete()
        db.query(AgentLocation).delete()
        db.query(Agent).delete()
        db.query(Employee).delete()
        db.query(Product).delete()
        db.query(Category).delete()
        db.query(Unit).delete()
        db.query(Warehouse).delete()
        db.query(CashRegister).delete()
        db.query(Partner).delete()
        db.query(User).filter(User.username != "admin").delete()  # faqat admin qoldiriladi
        db.commit()
        print("✅ Barcha namunaviy ma'lumotlar o'chirildi!")
        # Foydalanuvchi (admin)
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                full_name="Administrator",
                role="admin"
            )
            db.add(admin)
            print("вњ… Admin foydalanuvchi yaratildi")
        
        # O'lchov birliklari
        units = [
            {"code": "kg", "name": "Kilogramm"},
            {"code": "g", "name": "Gramm"},
            {"code": "dona", "name": "Dona"},
            {"code": "qop", "name": "Qop"},
            {"code": "litr", "name": "Litr"},
            {"code": "quti", "name": "Quti"},
            {"code": "paket", "name": "Paket"},
        ]
        for u in units:
            if not db.query(Unit).filter(Unit.code == u["code"]).first():
                db.add(Unit(**u))
        print("вњ… O'lchov birliklari yaratildi")
        
        # Kategoriyalar
        categories = [
            {"code": "HALVA", "name": "Halva", "type": "tayyor"},
            {"code": "KONFET", "name": "Konfetlar", "type": "tayyor"},
            {"code": "SHIRINLIK", "name": "Shirinliklar", "type": "tayyor"},
            {"code": "XOM_ASHYO", "name": "Xom ashyo", "type": "hom_ashyo"},
            {"code": "QADOQ", "name": "Qadoqlash materiallari", "type": "hom_ashyo"},
        ]
        for c in categories:
            if not db.query(Category).filter(Category.code == c["code"]).first():
                db.add(Category(**c))
        print("вњ… Kategoriyalar yaratildi")
        
        # Omborlar
        warehouses = [
            {"name": "Asosiy ombor", "code": "MAIN", "address": "Toshkent"},
            {"name": "Tayyor mahsulot", "code": "PROD", "address": "Ishlab chiqarish"},
            {"name": "Xom ashyo ombori", "code": "RAW", "address": "Xom ashyo"},
        ]
        for w in warehouses:
            if not db.query(Warehouse).filter(Warehouse.code == w["code"]).first():
                db.add(Warehouse(**w))
        print("вњ… Omborlar yaratildi")
        
        # Kassa
        if not db.query(CashRegister).first():
            cash = CashRegister(
                name="Asosiy kassa",
                balance=0
            )
            db.add(cash)
            print("вњ… Kassa yaratildi")
        
        db.commit()
        
        # Namuna mahsulotlar
        kg_unit = db.query(Unit).filter(Unit.code == "kg").first()
        dona_unit = db.query(Unit).filter(Unit.code == "dona").first()
        halva_cat = db.query(Category).filter(Category.code == "HALVA").first()
        xom_ashyo_cat = db.query(Category).filter(Category.code == "XOM_ASHYO").first()
        
        products = [
            {"name": "Halva oddiy", "code": "H001", "type": "tayyor", 
             "category_id": halva_cat.id if halva_cat else None,
             "unit_id": kg_unit.id if kg_unit else None,
             "purchase_price": 25000, "sale_price": 35000},
            {"name": "Halva shokoladli", "code": "H002", "type": "tayyor",
             "category_id": halva_cat.id if halva_cat else None,
             "unit_id": kg_unit.id if kg_unit else None,
             "purchase_price": 30000, "sale_price": 45000},
            {"name": "Halva yong'oqli", "code": "H003", "type": "tayyor",
             "category_id": halva_cat.id if halva_cat else None,
             "unit_id": kg_unit.id if kg_unit else None,
             "purchase_price": 35000, "sale_price": 55000},
            {"name": "Shakar", "code": "XA001", "type": "hom_ashyo",
             "category_id": xom_ashyo_cat.id if xom_ashyo_cat else None,
             "unit_id": kg_unit.id if kg_unit else None,
             "purchase_price": 12000, "sale_price": 0},
            {"name": "Kunjut", "code": "XA002", "type": "hom_ashyo",
             "category_id": xom_ashyo_cat.id if xom_ashyo_cat else None,
             "unit_id": kg_unit.id if kg_unit else None,
             "purchase_price": 45000, "sale_price": 0},
        ]
        
        for p in products:
            if not db.query(Product).filter(Product.code == p["code"]).first():
                db.add(Product(**p))
        print("вњ… Namuna mahsulotlar yaratildi")
        
        # Namuna kontragentlar
        partners = [
            {"name": "Namunaviy mijoz", "code": "M001", "type": "customer", "phone": "+998901234567"},
            {"name": "Namunaviy yetkazib beruvchi", "code": "YB001", "type": "supplier", "phone": "+998909876543"},
        ]
        for p in partners:
            if not db.query(Partner).filter(Partner.code == p["code"]).first():
                db.add(Partner(**p))
        print("вњ… Namuna kontragentlar yaratildi")
        
        # Namuna xodimlar
        employees = [
            {"full_name": "Namunaviy Xodim", "code": "X001", "position": "Ishchi", "department": "Ishlab chiqarish", "salary": 3000000},
        ]
        for e in employees:
            if not db.query(Employee).filter(Employee.code == e["code"]).first():
                db.add(Employee(**e))
        print("вњ… Namuna xodimlar yaratildi")
        
        # ====== SalesDoc funksiyalari ======
        
        # Namuna agentlar
        agents_data = [
            {"code": "AG001", "full_name": "Alisher Karimov", "phone": "+998901111111", "region": "Toshkent shahri", "telegram_id": "@alisher_agent"},
            {"code": "AG002", "full_name": "Botir Yusupov", "phone": "+998902222222", "region": "Toshkent viloyati", "telegram_id": "@botir_agent"},
            {"code": "AG003", "full_name": "Sardor Alimov", "phone": "+998903333333", "region": "Samarqand", "telegram_id": "@sardor_agent"},
            {"code": "AG004", "full_name": "Jamshid Raximov", "phone": "+998904444444", "region": "Buxoro", "telegram_id": "@jamshid_agent"},
        ]
        for a in agents_data:
            if not db.query(Agent).filter(Agent.code == a["code"]).first():
                agent = Agent(**a, is_active=True)
                db.add(agent)
                db.flush()
                
                # Har bir agent uchun lokatsiyalar
                base_lat = 41.311081 + random.uniform(-0.1, 0.1)
                base_lng = 69.240562 + random.uniform(-0.1, 0.1)
                for i in range(5):
                    loc = AgentLocation(
                        agent_id=agent.id,
                        latitude=base_lat + random.uniform(-0.01, 0.01),
                        longitude=base_lng + random.uniform(-0.01, 0.01),
                        accuracy=random.uniform(5, 50),
                        battery=random.randint(20, 100),
                        recorded_at=datetime.now() - timedelta(minutes=i*30)
                    )
                    db.add(loc)
        print("вњ… Namuna agentlar yaratildi")
        
        # Namuna haydovchilar
        drivers_data = [
            {"code": "DR001", "full_name": "Rustam Qodirov", "phone": "+998905555555", "vehicle_type": "truck", "vehicle_number": "01A123BC", "telegram_id": "@rustam_driver"},
            {"code": "DR002", "full_name": "Odil Nazarov", "phone": "+998906666666", "vehicle_type": "car", "vehicle_number": "01B456DE", "telegram_id": "@odil_driver"},
            {"code": "DR003", "full_name": "Shuhrat Toshmatov", "phone": "+998907777777", "vehicle_type": "truck", "vehicle_number": "01C789FG", "telegram_id": "@shuhrat_driver"},
        ]
        for d in drivers_data:
            if not db.query(Driver).filter(Driver.code == d["code"]).first():
                driver = Driver(**d, is_active=True)
                db.add(driver)
                db.flush()
                
                # Har bir haydovchi uchun lokatsiyalar
                base_lat = 41.311081 + random.uniform(-0.15, 0.15)
                base_lng = 69.240562 + random.uniform(-0.15, 0.15)
                for i in range(10):
                    loc = DriverLocation(
                        driver_id=driver.id,
                        latitude=base_lat + random.uniform(-0.02, 0.02),
                        longitude=base_lng + random.uniform(-0.02, 0.02),
                        speed=random.uniform(0, 60) if i < 5 else 0,
                        recorded_at=datetime.now() - timedelta(minutes=i*15)
                    )
                    db.add(loc)
        print("вњ… Namuna haydovchilar yaratildi")
        
        # Mijozlar lokatsiyalari
        partners = db.query(Partner).filter(Partner.type == "customer").all()
        for p in partners:
            if not db.query(PartnerLocation).filter(PartnerLocation.partner_id == p.id).first():
                ploc = PartnerLocation(
                    partner_id=p.id,
                    latitude=41.311081 + random.uniform(-0.08, 0.08),
                    longitude=69.240562 + random.uniform(-0.08, 0.08),
                    address=p.address or "Toshkent"
                )
                db.add(ploc)
        print("вњ… Mijoz lokatsiyalari yaratildi")
        
        # ====== RETSEPTLAR ======
        # Halva oddiy retsepti
        halva_product = db.query(Product).filter(Product.code == "H001").first()
        shakar = db.query(Product).filter(Product.code == "XA001").first()
        kunjut = db.query(Product).filter(Product.code == "XA002").first()
        
        if halva_product and not db.query(Recipe).filter(Recipe.name == "Halva oddiy").first():
            recipe1 = Recipe(
                name="Halva oddiy",
                product_id=halva_product.id,
                output_quantity=1,
                description="Klassik halva retsepti",
                is_active=True
            )
            db.add(recipe1)
            db.flush()
            
            # Tarkibi
            if shakar:
                db.add(RecipeItem(recipe_id=recipe1.id, product_id=shakar.id, quantity=0.5))
            if kunjut:
                db.add(RecipeItem(recipe_id=recipe1.id, product_id=kunjut.id, quantity=0.4))
            print("вњ… Halva oddiy retsepti yaratildi")
        
        # Halva shokoladli retsepti
        halva_shok = db.query(Product).filter(Product.code == "H002").first()
        if halva_shok and not db.query(Recipe).filter(Recipe.name == "Halva shokoladli").first():
            recipe2 = Recipe(
                name="Halva shokoladli",
                product_id=halva_shok.id,
                output_quantity=1,
                description="Shokolad qo'shilgan halva",
                is_active=True
            )
            db.add(recipe2)
            db.flush()
            
            if shakar:
                db.add(RecipeItem(recipe_id=recipe2.id, product_id=shakar.id, quantity=0.4))
            if kunjut:
                db.add(RecipeItem(recipe_id=recipe2.id, product_id=kunjut.id, quantity=0.35))
            print("вњ… Halva shokoladli retsepti yaratildi")
        
        # Halva yong'oqli retsepti
        halva_yongoq = db.query(Product).filter(Product.code == "H003").first()
        if halva_yongoq and not db.query(Recipe).filter(Recipe.name == "Halva yong'oqli").first():
            recipe3 = Recipe(
                name="Halva yong'oqli",
                product_id=halva_yongoq.id,
                output_quantity=1,
                description="Yong'oq qo'shilgan premium halva",
                is_active=True
            )
            db.add(recipe3)
            db.flush()
            
            if shakar:
                db.add(RecipeItem(recipe_id=recipe3.id, product_id=shakar.id, quantity=0.35))
            if kunjut:
                db.add(RecipeItem(recipe_id=recipe3.id, product_id=kunjut.id, quantity=0.3))
            print("вњ… Halva yong'oqli retsepti yaratildi")
        
        db.commit()
        print("\nрџЋ‰ Barcha boshlang'ich ma'lumotlar muvaffaqiyatli yaratildi!")
        
    except Exception as e:
        db.rollback()
        print(f"вќЊ Xatolik: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    init_data()

