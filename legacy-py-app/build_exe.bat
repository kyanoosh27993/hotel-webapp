@echo off
REM ============================================================
REM  ساخت فایل exe ویندوز — سیستم جامع حضور و غیاب و حقوق و دستمزد
REM  نسخه ۰.۱.۰  —  فقط کافی است این فایل را دابل‌کلیک کنید
REM ============================================================
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ============================================
echo   ساخت فایل exe برنامه حقوق و دستمزد
echo ============================================
echo.

REM --- بررسی پایتون ---
where python >nul 2>nul
if errorlevel 1 (
    echo [خطا] پایتون نصب نیست!
    echo 1- به python.org بروید و Python 3.11 یا جدیدتر را نصب کنید
    echo 2- حتما گزینه Add Python to PATH را هنگام نصب تیک بزنید
    pause
    exit /b 1
)

REM --- نصب پیش‌نیازها ---
echo [1/3] نصب پیش‌نیازها ...
python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [خطا] نصب پیش‌نیازها ناموفق بود - اتصال اینترنت را بررسی کنید
    pause
    exit /b 1
)

REM --- ساخت exe ---
echo [2/3] ساخت فایل exe (چند دقیقه طول می‌کشد) ...
python -m PyInstaller payroll.spec --noconfirm --clean
if errorlevel 1 (
    echo [خطا] ساخت exe ناموفق بود
    pause
    exit /b 1
)

REM --- ساخت پوشه تحویل ---
echo [3/3] آماده‌سازی پوشه تحویل ...
set OUT=خروجی_برنامه
if exist "%OUT%" rmdir /s /q "%OUT%"
mkdir "%OUT%"
copy dist\PayrollSystem_v0.3.0.exe "%OUT%\" >nul
mkdir "%OUT%\data" 2>nul

echo.
echo ============================================
echo   ✔ ساخت با موفقیت انجام شد!
echo   فایل exe در پوشه «%OUT%» قرار گرفت
echo   نام فایل: PayrollSystem_v0.3.0.exe
echo   ورود پیش‌فرض: کاربر admin / رمز admin123
echo ============================================
echo.
explorer "%OUT%"
pause
