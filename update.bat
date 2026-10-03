@echo off
setlocal enabledelayedexpansion

REM Usage:
REM   update.bat                       pull, rebuild, test, restart local server
REM   update.bat --local               rebuild + test only (no git pull / server)
REM   update.bat --export-gst YYYY-MM  export one month of bills -> Tally/GST files
REM   update.bat --export-gst all      export every saved month -> Tally/GST files

set "REPO_DIR=%~dp0"
cd /d "%REPO_DIR%" || exit /b 1

REM ── Find python executable ──────────────────────────────────────────────────
if exist "%REPO_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%REPO_DIR%.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

REM ── GST export shortcut ─────────────────────────────────────────────────────
if /i "%~1"=="--export-gst" goto :export_gst
if /i "%~1"=="/export-gst" goto :export_gst
goto :check_mode

:export_gst
set "MONTH=%~2"
if "%MONTH%"=="" (
    echo Usage: update.bat --export-gst YYYY-MM   ^(or 'all' for every month^)
    exit /b 1
)
echo =======================================================
echo   S. KUMAR ^& BROS - GST EXPORT
echo =======================================================
if /i "%MONTH%"=="all" (
    echo Exporting ALL saved months -^> Tally DayBook -^> GST JSON...
    "%PYTHON_EXE%" src\seller\prepare_tally_files.py --all
) else (
    echo Exporting %MONTH% -^> Tally DayBook -^> GST JSON...
    "%PYTHON_EXE%" src\seller\prepare_tally_files.py --month "%MONTH%"
)
if errorlevel 1 (
    echo.
    echo ERROR: GST export failed.
    exit /b 1
)
echo.
echo =======================================================
echo   EXPORT COMPLETE!
echo   GST files: TallyToOutputsForGST\output\
echo   Upload the .json to https://gst.gov.in ^(GSTR-1^)
echo =======================================================
exit /b 0

:check_mode
set "LOCAL_ONLY=0"
if /i "%~1"=="--local" set "LOCAL_ONLY=1"
if /i "%~1"=="/local" set "LOCAL_ONLY=1"

echo =======================================================
echo         S. KUMAR ^& BROS - CATALOG UPDATER
echo =======================================================
echo.

if "%LOCAL_ONLY%"=="0" (
    echo Pulling latest changes...
    git pull origin main
    if errorlevel 1 (
        echo ERROR: Git pull failed.
        exit /b 1
    )
)

echo Rebuilding the catalogs from the current CSV, templates, and images...
"%PYTHON_EXE%" src\build_catalog.py
if errorlevel 1 (
    echo ERROR: Catalog build failed.
    exit /b 1
)

echo Running tests...
"%PYTHON_EXE%" -m unittest discover -s tests
if errorlevel 1 (
    echo ERROR: Python unit tests failed.
    exit /b 1
)

for %%f in (tests\*.test.js) do (
    if exist "%%f" (
        node "%%f"
        if errorlevel 1 (
            echo ERROR: JavaScript test %%f failed.
            exit /b 1
        )
    )
)

if "%LOCAL_ONLY%"=="1" (
    echo.
    echo =======================================================
    echo   UPDATE COMPLETE ^(local mode^): rebuilt and tested locally.
    echo =======================================================
    exit /b 0
)

echo Restarting local seller server...
REM Kill old server via PID if server.pid exists
if exist "server.pid" (
    for /f "usebackq delims=" %%p in ("server.pid") do (
        set "OLD_PID=%%p"
        if defined OLD_PID (
            taskkill /F /PID !OLD_PID! >nul 2>&1
        )
    )
    del /f /q "server.pid" >nul 2>&1
)

REM Kill any remaining process listening on port 8766
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8766 ^| findstr LISTENING') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Start new server in background and record output to server.log
powershell -NoProfile -ExecutionPolicy Bypass -Command "$psi = New-Object System.Diagnostics.ProcessStartInfo; $psi.FileName = 'cmd.exe'; $psi.Arguments = '/c """%PYTHON_EXE%"" -u src\seller\local_seller.py > server.log 2>&1'; $psi.WindowStyle = 'Hidden'; $psi.CreateNoWindow = $true; [System.Diagnostics.Process]::Start($psi) | Out-Null"

REM Allow brief startup time to initialize socket (portable delay)
ping 127.0.0.1 -n 3 >nul

REM Record listening PID to server.pid
set "SERVER_PID="
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8766 ^| findstr LISTENING') do (
    set "SERVER_PID=%%a"
    echo %%a> "server.pid"
)

if defined SERVER_PID (
    echo Server started ^(PID !SERVER_PID!^).
) else (
    echo Server started.
)

echo.
echo =======================================================
echo   UPDATE COMPLETE!
echo   The app is running at: http://127.0.0.1:8766/?edit=true
echo =======================================================
exit /b 0
