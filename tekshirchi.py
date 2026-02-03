# -*- coding: utf-8 -*-
"""Totli Holva tizimini tekshirish: server, baza, production sahifasi."""
import sys
import os
import socket
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PORT = 8080
BASE = f"http://127.0.0.1:{PORT}"

def port_ochiq(port):
    """Port band yoki ochiq tekshirish."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except Exception:
        return False

def baza_omborlari():
    """Bazadagi omborlar ro'yxati."""
    try:
        from app.models.database import SessionLocal, Warehouse
        db = SessionLocal()
        try:
            warehouses = db.query(Warehouse).all()
            return len(warehouses), [w.name for w in warehouses]
        finally:
            db.close()
    except Exception as e:
        return None, str(e)

def production_sahifasi():
    """Login qilib /production sahifasida omborlar dropdown da bormi."""
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    try:
        data = urllib.parse.urlencode({"username": "admin", "password": "admin123"}).encode()
        req = urllib.request.Request(f"{BASE}/login", data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        r = opener.open(req)
        r.read()
    except urllib.error.HTTPError as e:
        if e.code != 303:
            return False, f"Login: {e.code}"
        if e.fp:
            e.fp.read()
    except Exception as e:
        return False, str(e)
    try:
        r = opener.open(urllib.request.Request(f"{BASE}/production"))
        html = r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return False, "HTTP %s" % e.code
    except Exception as e:
        return False, str(e)
    # value="123" yoki value='123' va boshqa bo'shliq/attribute lar
    options = re.findall(r'<option\s+value=["\']?(\d+)["\']?[^>]*>([^<]+)</option>', html)
    wh_opts = [n.strip() for _, n in options if _ and "Tanlang" not in n and n.strip()]
    bosh_xabar = "Omborlar ro'yxati bo'sh" in html
    # Login sahifasida "Kirish" yoki "Parol" bo'ladi; production da "Ishlab chiqarish" yoki "Tezkor ishlab chiqarish"
    login_sahifa = "Kirish" in html or ("Parol" in html and "Ishlab chiqarish" not in html)
    if login_sahifa and len(wh_opts) == 0:
        return False, "Session saqlanmadi – login sahifasi qaytdi. Brauzerda /production ni qo'lda tekshiring."
    return len(wh_opts) > 0 and not bosh_xabar, (wh_opts, bosh_xabar)

def main():
    print("=" * 50)
    print("  TOTLI HOLVA - TEKSHIRCHI")
    print("=" * 50)
    print()

    # 1) Server
    print("[1] Server (port %s)..." % PORT)
    if port_ochiq(PORT):
        print("    OK - Server ishlayapti.")
    else:
        print("    XATO - Server ishlamayapti. server_manager.bat dan ishga tushiring.")
    print()

    # 2) Baza - omborlar
    print("[2] Baza - omborlar...")
    n, res = baza_omborlari()
    if n is not None:
        print("    OK - Bazada %s ta ombor." % n)
        for name in res:
            print("        - %s" % name)
        if n == 0:
            print("    OGOH - Ma'lumotnomalar > Omborlar orqali ombor qo'shing.")
    else:
        print("    XATO - Baza: %s" % res)
    print()

    # 3) Production sahifasi (faqat server ishlasa)
    print("[3] Production sahifasi (omborlar dropdown)...")
    if not port_ochiq(PORT):
        print("    O'tkazib yuborildi - server ishlamayapti.")
    else:
        ok, val = production_sahifasi()
        if ok:
            print("    OK - Ishlab chiqarish sahifasida omborlar tanlanadi.")
        else:
            if isinstance(val, tuple):
                opts, bosh = val
                if bosh:
                    print("    XATO - Sahifada 'Omborlar ro'yxati bo'sh' ko'rinadi.")
                else:
                    print("    XATO - Dropdown da omborlar yo'q.")
            else:
                print("    XATO - %s" % val)
    print()
    print("=" * 50)
    if sys.stdin.isatty():
        try:
            input("Chiqish uchun Enter bosing...")
        except EOFError:
            pass

if __name__ == "__main__":
    main()
