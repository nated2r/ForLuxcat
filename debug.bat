@echo off
chcp 65001 >nul
echo =======================================
echo  FuMao Calculator - Debug Mode
echo =======================================
echo.
echo [1] Run crawler to update product data (update_data.py)
echo [2] Start local web preview (http://localhost:8000)
echo.
set /p choice=Enter option (1 or 2):

if "%choice%"=="1" (
    cd /d %~dp0
    call venv\Scripts\activate.bat
    python update_data.py
    echo.
    echo Done! Please check if web/products.json was generated correctly.
)
if "%choice%"=="2" (
    cd /d %~dp0\web
    echo Starting local server...
    python -m http.server 8000
)
pause
