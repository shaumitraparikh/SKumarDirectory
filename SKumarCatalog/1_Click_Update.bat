@echo off
setlocal
title Catalog Builder Update
color 0A
echo =======================================================
echo         S. KUMAR & BROS - CATALOG UPDATER
echo =======================================================
echo.
echo Rebuilding your catalogs from the latest CSV data...
echo.

set "EXIT_CODE=0"
set "REPO_DIR=%~dp0.."
cd /d "%REPO_DIR%" || goto :error

for /f "delims=" %%B in ('git branch --show-current') do set "CURRENT_BRANCH=%%B"
if not "%CURRENT_BRANCH%"=="main" goto :wrong_branch

cd /d "%~dp0" || goto :error
python build_catalog.py
if errorlevel 1 goto :error

cd /d "%REPO_DIR%" || goto :error
git add -- SKumarCatalog/output/print_catalog.html SKumarCatalog/output/search_catalog.html
if errorlevel 1 goto :error

git commit --allow-empty -m "Update generated catalogs" --only -- SKumarCatalog/output/print_catalog.html SKumarCatalog/output/search_catalog.html
if errorlevel 1 goto :error

git push origin main
if errorlevel 1 goto :error

echo.
echo =======================================================
echo  UPDATE AND PUSH COMPLETE!
echo  GitHub Actions will deploy the catalogs to GitHub Pages.
echo =======================================================
echo.
goto :finish

:wrong_branch
echo ERROR: Run this updater from the main branch so Pages can be updated.
set "EXIT_CODE=1"
goto :finish

:error
echo.
echo ERROR: Catalog update, commit, or push failed. Review the messages above.
set "EXIT_CODE=1"

:finish
pause
exit /b %EXIT_CODE%
