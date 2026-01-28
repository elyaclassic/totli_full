"""
Admin foydalanuvchisining parolini yangilash
"""
from app.models.database import get_db, User
from app.utils.auth import hash_password

def update_admin_password():
    """Admin parolini hash qilish"""
    db = next(get_db())
    
    # Admin foydalanuvchisini topish
    admin = db.query(User).filter(User.username == "admin").first()
    
    if not admin:
        print("❌ Admin foydalanuvchisi topilmadi!")
        print("💡 Iltimos, avval admin foydalanuvchisini yarating.")
        return
    
    # Parolni hash qilish
    new_password_hash = hash_password("admin123")
    admin.password_hash = new_password_hash
    
    db.commit()
    print("✅ Admin parol muvaffaqiyatli yangilandi!")
    print(f"   Username: admin")
    print(f"   Password: admin123")
    print(f"   Hash: {new_password_hash[:50]}...")
    
    db.close()

if __name__ == "__main__":
    update_admin_password()
