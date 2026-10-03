@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM Usage:
REM   update.bat                       pull, rebuild, test, restart local server
REM   update.bat --local               rebuild + test only (no git pull / server)
REM   update.bat --export-gst YYYY-MM  export one month of bills -> Tally/GST files
REM   update.bat --export-gst all      export every saved month -> Tally/GST files

set "REPO_DIR=%~dp0"
cd /d "%REPO_DIR%" || exit /b 1

REM ── Find python executable ──────────────────────────────────────────────────
set "PYTHON_CMD="
if exist "%REPO_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_CMD="%REPO_DIR%.venv\Scripts\python.exe""
) else (
    py -3 -c "import sys; sys.exit(0)" >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_CMD=py -3"
    ) else (
        python -c "import sys; sys.exit(0)" >nul 2>&1
        if not errorlevel 1 (
            set "PYTHON_CMD=python"
        ) else (
            python3 -c "import sys; sys.exit(0)" >nul 2>&1
            if not errorlevel 1 (
                set "PYTHON_CMD=python3"
            ) else (
                echo ERROR: Python 3 was not found. Please install Python from https://www.python.org/
                exit /b 1
            )
        )
    )
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
    %PYTHON_CMD% src\seller\prepare_tally_files.py --all
) else (
    echo Exporting %MONTH% -^> Tally DayBook -^> GST JSON...
    %PYTHON_CMD% src\seller\prepare_tally_files.py --month "%MONTH%"
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
    where git >nul 2>&1
    if not errorlevel 1 (
        git restore index.html photo_catalog.html print_catalog.html >nul 2>&1
        git pull origin main
        if errorlevel 1 (
            echo WARNING: Git pull encountered an issue. Proceeding with local rebuild...
        )
    ) else (
        echo WARNING: Git is not installed or not in PATH. Skipping pull...
    )
)

echo Rebuilding the catalogs from the current data (XLSX/CSV), templates, and images...
%PYTHON_CMD% src\build_catalog.py
if errorlevel 1 goto :error

echo Running tests...
%PYTHON_CMD% -m unittest discover -s tests
if errorlevel 1 goto :error

where node >nul 2>&1
if not errorlevel 1 (
    for %%f in (tests\*.test.js) do (
        if exist "%%f" (
            node "%%f"
            if errorlevel 1 goto :error
        )
    )
) else (
    echo Note: Node.js not detected; skipping front-end test assertions.
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
    if not "%%a"=="0" taskkill /F /PID %%a >nul 2>&1
)

REM Start new server minimized in background
start "SKumar Local Server" /d "%REPO_DIR%" /min %PYTHON_CMD% src\seller\local_seller.py

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
echo   Opening http://127.0.0.1:8766/?edit=true in browser...
echo =======================================================
start "" "http://127.0.0.1:8766/?edit=true"
echo.
echo Press any key to close this window...
pause >nul
exit /b 0

:error
echo.
echo =======================================================
echo   ERROR: Update encountered an issue. See details above.
echo =======================================================
echo.
pause
exit /b 1
