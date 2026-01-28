"""
Parolni tekshirish
"""
from app.utils.auth import hash_password, verify_password
from app.models.database import get_db, User

# Admin foydalanuvchisini olish
db = next(get_db())
admin = db.query(User).filter(User.username == "admin").first()

print("=" * 60)
print("ADMIN MA'LUMOTLARI:")
print("=" * 60)
print(f"Username: {admin.username}")
print(f"Password Hash: {admin.password_hash}")
print(f"Is Active: {admin.is_active}")
print()

# Parolni tekshirish
test_password = "admin123"
test_hash = hash_password(test_password)

print("=" * 60)
print("PAROL TEKSHIRUVI:")
print("=" * 60)
print(f"Test Password: {test_password}")
print(f"Test Hash: {test_hash}")
print(f"Admin Hash: {admin.password_hash}")
print(f"Hashes Match: {test_hash == admin.password_hash}")
print()

# Verify funksiyasini tekshirish
result = verify_password(test_password, admin.password_hash)
print(f"verify_password() result: {result}")

db.close()
