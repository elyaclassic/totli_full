@echo off
title TOTLI HOLVA Business System
echo ========================================
echo   TOTLI HOLVA Biznes Tizimi
echo ========================================
echo.

cd /d "%~dp0"

:: Python borligini tekshirish
python --version > nul 2>&1
if errorlevel 1 (
    echo [X] Python topilmadi!
    echo Python 3.8+ o'rnating: https://python.org
    pause
    exit /b 1
)

:: Kutubxonalar o'rnatish
echo [1/3] Kutubxonalar tekshirilmoqda...
pip install -r requirements.txt -q

:: Ma'lumotlar bazasini yaratish
echo [2/3] Ma'lumotlar bazasi yaratilmoqda...
:: python init_data.py

:: Serverni ishga tushirish
echo [3/3] Server ishga tushirilmoqda...
echo.
echo ========================================
echo   Brauzerda oching: http://10.243.49.144:8080
echo ========================================
echo.
echo Chiqish uchun Ctrl+C bosing
echo.

python -m uvicorn main:app --host 10.243.49.144 --port 8080 --reload

pause
