@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
echo ============================================
echo   بناء setup.exe لنظام إدارة الأعمال (خطوة واحدة)
echo ============================================
echo.

cd /d "%~dp0.."

REM ---------------------------------------------------------
REM [1/4] التحقق من وجود Python
REM ---------------------------------------------------------
where python >nul 2>nul
if errorlevel 1 (
    echo [خطأ] لم يتم العثور على Python.
    echo يرجى تثبيته أولاً من: https://www.python.org/downloads/
    echo تأكد من تفعيل خيار "Add Python to PATH" أثناء التثبيت.
    pause
    exit /b 1
)

echo [1/4] تثبيت المتطلبات (Flask + waitress + PyInstaller)...
pip install -r build\requirements_build.txt --quiet
if errorlevel 1 (
    echo [خطأ] فشل تثبيت المتطلبات.
    pause
    exit /b 1
)

REM ---------------------------------------------------------
REM [2/4] بناء الملف التنفيذي عبر PyInstaller
REM ---------------------------------------------------------
echo.
echo [2/4] حذف نواتج بناء سابقة...
rmdir /s /q build_output 2>nul
rmdir /s /q dist 2>nul
rmdir /s /q dist_installer 2>nul
del /q ERP_System.spec 2>nul

echo.
echo [3/4] بناء الملف التنفيذي (قد يستغرق دقيقة أو أكثر)...
pyinstaller --noconfirm --onefile --name "ERP_System" ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --add-data "database;database" ^
    --hidden-import waitress ^
    --distpath dist ^
    --workpath build_output ^
    launcher.py

if errorlevel 1 (
    echo [خطأ] فشلت عملية بناء الملف التنفيذي.
    pause
    exit /b 1
)

if not exist "dist\ERP_System.exe" (
    echo [خطأ] لم يتم إنشاء dist\ERP_System.exe
    pause
    exit /b 1
)

REM ---------------------------------------------------------
REM [4/4] إيجاد Inno Setup Compiler (ISCC.exe) وإنشاء setup.exe تلقائياً
REM ---------------------------------------------------------
echo.
echo [4/4] البحث عن Inno Setup Compiler لإنشاء setup.exe...

set "ISCC="
where ISCC.exe >nul 2>nul
if not errorlevel 1 (
    set "ISCC=ISCC.exe"
)

if not defined ISCC (
    if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
)
if not defined ISCC (
    if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
)
if not defined ISCC (
    if exist "%ProgramFiles(x86)%\Inno Setup 5\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 5\ISCC.exe"
)

if not defined ISCC (
    echo.
    echo ============================================
    echo   [تنبيه] لم يتم العثور على Inno Setup.
    echo   تم إنشاء الملف التنفيذي بنجاح: dist\ERP_System.exe
    echo   لكن لم يُنشأ setup.exe لأن Inno Setup غير مثبّت.
    echo.
    echo   ثبّت Inno Setup من: https://jrsoftware.org/isdl.php
    echo   ثم أعد تشغيل هذا الملف مرة أخرى ليكتمل إنشاء setup.exe تلقائياً.
    echo ============================================
    pause
    exit /b 0
)

echo تم العثور على Inno Setup: !ISCC!
echo جارٍ إنشاء setup.exe ...
"!ISCC!" "build\installer.iss"

if errorlevel 1 (
    echo [خطأ] فشل إنشاء setup.exe عبر Inno Setup.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   تم بنجاح! ملف التثبيت جاهز في:
echo   dist_installer\setup.exe
echo ============================================
pause
