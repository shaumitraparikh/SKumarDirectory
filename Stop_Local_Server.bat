@echo off
TITLE Stop SKumar Local Server
echo Stopping SKumar Local Server (Port 8766)...

set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8766') do (
    set FOUND=1
    echo Killing process %%a...
    taskkill /F /PID %%a >nul 2>&1
)

if "%FOUND%"=="0" (
    echo Server is not currently running.
) else (
    echo Server successfully stopped!
)

ping 127.0.0.1 -n 4 >nul
exit /b
