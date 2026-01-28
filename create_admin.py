"""
Admin foydalanuvchini yaratish
"""
from app.models.database import get_db, User, init_db
from app.utils.auth import hash_password

# Database yaratish
init_db()

# Database session
db = next(get_db())

# Admin foydalanuvchini tekshirish
admin = db.query(User).filter(User.username == "admin").first()

if admin:
    print("⚠️ Admin foydalanuvchisi allaqachon mavjud!")
    print(f"Username: {admin.username}")
    print(f"Is Active: {admin.is_active}")
else:
    # Admin yaratish
    admin = User(
        username="admin",
        password_hash=hash_password("admin123"),
        full_name="Administrator",
        role="admin",
        is_active=True
    )
    db.add(admin)
    db.commit()
    print("✅ Admin foydalanuvchisi yaratildi!")
    print("Username: admin")
    print("Password: admin123")

db.close()
