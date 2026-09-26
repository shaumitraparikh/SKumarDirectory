@echo off
setlocal
title Catalog Builder Update
color 0A
echo =======================================================
echo         S. KUMAR ^& BROS - CATALOG UPDATER
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
git add -A -- SKumarCatalog/config.json SKumarCatalog/data/catalog_data.csv SKumarCatalog/images SKumarCatalog/output/print_catalog.html SKumarCatalog/output/search_catalog.html
if errorlevel 1 goto :error

git diff --cached --quiet -- SKumarCatalog/config.json SKumarCatalog/data/catalog_data.csv SKumarCatalog/images SKumarCatalog/output/print_catalog.html SKumarCatalog/output/search_catalog.html
if errorlevel 2 goto :error
if errorlevel 1 goto :commit_changes
echo No catalog, image, or configuration changes to commit.
goto :confirm_push

:commit_changes
git commit -m "Update generated catalogs" --only -- SKumarCatalog/config.json SKumarCatalog/data/catalog_data.csv SKumarCatalog/images SKumarCatalog/output/print_catalog.html SKumarCatalog/output/search_catalog.html
if errorlevel 1 goto :error

:confirm_push
echo.
set "PUSH_CONFIRM=N"
set /p "PUSH_CONFIRM=Push catalog updates to origin/main and deploy GitHub Pages? [Y/N] "
if /i not "%PUSH_CONFIRM%"=="Y" goto :skip_push

git push origin main
if errorlevel 1 goto :error

echo.
echo =======================================================
echo  UPDATE AND PUSH COMPLETE!
echo  GitHub Actions will deploy the catalogs to GitHub Pages.
echo =======================================================
echo.
goto :finish

:skip_push
echo.
echo Catalog changes are saved in a local commit and were not pushed.
echo GitHub Pages will remain unchanged until you approve a push.
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
