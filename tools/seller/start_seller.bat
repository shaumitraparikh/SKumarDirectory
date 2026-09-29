@echo off
setlocal
set "REPO_DIR=%~dp0..\.."
cd /d "%REPO_DIR%" || exit /b 1

if not exist "index.html" (
    if exist ".venv\Scripts\python.exe" (
        ".venv\Scripts\python.exe" build_catalog.py
    ) else (
        python build_catalog.py
    )
    if errorlevel 1 exit /b 1
)

start "" "http://127.0.0.1:8766/index.html"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" tools\seller\local_seller.py
) else (
    python tools\seller\local_seller.py
)
endlocal
