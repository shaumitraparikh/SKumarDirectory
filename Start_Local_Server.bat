@echo off
TITLE Start SKumar Local Server
cd /d "%~dp0"

echo Checking if server is already running...
netstat -ano | findstr :8766 >nul
if %ERRORLEVEL% equ 0 (
    echo Server is already running on port 8766!
    start "" "http://127.0.0.1:8766/search_catalog.html"
    ping 127.0.0.1 -n 4 >nul
    exit /b
)

echo Starting SKumar Local Server...
start "SKumar Local Server" cmd /k "tools\seller\start_seller.bat"
exit /b
