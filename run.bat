@echo off
chcp 65001 >nul
echo ===============================================
echo   AI Clip Creator - Starting...
echo ===============================================
echo.

set "APP_DIR=%~dp0"
set "VENV_DIR=%APP_DIR%venv312"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "MAIN_SCRIPT=%APP_DIR%main.py"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] Virtual environment tidak ditemukan di:
    echo   %PYTHON_EXE%
    echo.
    echo Silakan jalankan installer.bat terlebih dahulu.
    pause
    exit /b 1
)

if not exist "%MAIN_SCRIPT%" (
    echo [ERROR] File main.py tidak ditemukan!
    pause
    exit /b 1
)

echo [INFO] Menggunakan Python: %PYTHON_EXE%
echo [INFO] Log file: %APP_DIR%app.log
echo [INFO] Tekan CTRL+C untuk menghentikan server
echo.
echo ===============================================
echo   Server akan berjalan di: http://localhost:5000
echo   Buka browser untuk mengakses aplikasi
echo ===============================================
echo.

"%PYTHON_EXE%" "%MAIN_SCRIPT%"

echo.
echo [INFO] Server dihentikan.
pause
