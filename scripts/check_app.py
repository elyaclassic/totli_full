"""
TOTLI Business System — tezkor tekshiruv.
Ishga tushirish: loyiha ildizida  python scripts/check_app.py
Yoki:  py scripts/check_app.py
"""
import sys
import os

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

def main():
    errors = []
    print("=" * 50)
    print("TOTLI Business System — tekshiruv")
    print("=" * 50)

    # 1. Import app
    print("\n1. main:app import...")
    try:
        from main import app
        print("   OK")
    except Exception as e:
        errors.append(f"main import: {e}")
        print(f"   XATO: {e}")
        return 1

    # 2. TestClient
    print("\n2. TestClient orqali route'lar...")
    try:
        from fastapi.testclient import TestClient
        client = TestClient(app)
    except Exception as e:
        errors.append(f"TestClient: {e}")
        print(f"   XATO: {e}")
        return 1

    checks = [
        ("/ping", 200, "ping"),
        ("/login", 200, "login sahifa"),
        ("/favicon.ico", [200, 204], "favicon"),
    ]
    for path, expected, name in checks:
        try:
            r = client.get(path)
            ok = r.status_code == expected if isinstance(expected, int) else r.status_code in expected
            if ok:
                print(f"   GET {path} -> {r.status_code} OK ({name})")
            else:
                print(f"   GET {path} -> {r.status_code} (kutilgan {expected})")
                errors.append(f"{path}: {r.status_code}")
        except Exception as e:
            print(f"   GET {path} -> XATO: {e}")
            errors.append(f"{path}: {e}")

    # 3. /docs (development da ochiq bo'lishi kerak)
    print("\n3. /docs (PRODUCTION da yopiq)...")
    try:
        r = client.get("/docs")
        prod = os.getenv("PRODUCTION", "").lower() in ("1", "true", "yes")
        if prod and r.status_code == 200:
            print("   Ogohlantirish: PRODUCTION=1 bo'lsa /docs 404 bo'lishi kerak")
        elif not prod and r.status_code == 200:
            print("   GET /docs -> 200 OK")
        elif not prod and r.status_code != 200:
            errors.append(f"/docs: {r.status_code}")
        else:
            print("   GET /docs -> 404 (production)")
    except Exception as e:
        print(f"   XATO: {e}")

    # 4. Himoyalangan route login ga yo'naltirishi
    print("\n4. /products (auth kerak -> login ga redirect)...")
    try:
        r = client.get("/products", follow_redirects=False)
        if r.status_code in (302, 303) and "/login" in (r.headers.get("location") or ""):
            print("   OK (login ga yo'naltirildi)")
        elif r.status_code == 200:
            print("   OK (sahifa ochildi — cookie bor bo'lishi mumkin)")
        else:
            print(f"   Status: {r.status_code}")
    except Exception as e:
        print(f"   XATO: {e}")

    # 5. Audit log va backup modullari
    print("\n5. Audit log va backup modullari...")
    try:
        from app.utils.audit_log import log_audit
        from app.utils.backup import run_backup, get_db_path
        log_audit(None, "check", "test", None)
        p = get_db_path()
        print(f"   audit_log OK, get_db_path OK: {os.path.basename(p)}")
    except Exception as e:
        errors.append(f"utils: {e}")
        print(f"   XATO: {e}")

    print("\n" + "=" * 50)
    if errors:
        print("XATOLAR:", len(errors))
        for e in errors:
            print("  -", e)
        return 1
    print("Barcha tekshiruvlar o'tdi.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
