@echo off
setlocal
title Catalog Builder Update
color 0A
echo =======================================================
echo         S. KUMAR ^& BROS - CATALOG UPDATER
echo =======================================================
echo.
echo Rebuilding the catalogs from the current CSV, templates, and images...
echo.

set "EXIT_CODE=0"
set "REPO_DIR=%~dp0"
cd /d "%REPO_DIR%" || goto :error

for /f "delims=" %%B in ('git branch --show-current') do set "CURRENT_BRANCH=%%B"
if not "%CURRENT_BRANCH%"=="main" goto :wrong_branch

echo Checking that main is synchronized with origin...
git fetch origin main
if errorlevel 1 goto :error
for /f "delims=" %%H in ('git rev-parse HEAD') do set "LOCAL_HEAD=%%H"
for /f "delims=" %%H in ('git rev-parse origin/main') do set "REMOTE_HEAD=%%H"
if not "%LOCAL_HEAD%"=="%REMOTE_HEAD%" goto :branch_out_of_date

python build_catalog.py
if errorlevel 1 goto :error

python -m unittest discover -s tests -p "test_*.py"
if errorlevel 1 goto :error

node tests/order_core.test.js
if errorlevel 1 goto :error

cd /d "%REPO_DIR%" || goto :error
echo.
set /p "PUBLISH_CHANGES=Commit and push these catalog changes to origin/main? (Y/N): "
if /I not "%PUBLISH_CHANGES%"=="Y" goto :declined

git add -A
if errorlevel 1 goto :error

git diff --cached --quiet
if errorlevel 2 goto :error
if errorlevel 1 goto :commit_changes
echo No catalog changes to commit. GitHub Pages is already up to date.
goto :finish

:commit_changes
git commit -m "Update generated catalogs" -m "Rebuild GitHub Pages output from tested catalog sources." -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
if errorlevel 1 goto :error

echo.
echo Pushing the catalog update to origin/main...
git push origin HEAD:main
if errorlevel 1 goto :error

echo =======================================================
echo  UPDATE PUSHED SUCCESSFULLY!
echo  GitHub Actions will deploy the catalogs to GitHub Pages.
echo =======================================================
echo.
goto :finish

:wrong_branch
echo ERROR: Run this updater from the main branch so Pages can be updated.
set "EXIT_CODE=1"
goto :finish

:branch_out_of_date
echo ERROR: Local main is not exactly synchronized with origin/main.
echo Sync or resolve the branch first, then rerun this updater.
echo No catalog changes were built, committed, or pushed.
set "EXIT_CODE=1"
goto :finish

:declined
echo Catalogs were rebuilt and tested, but not committed or pushed.
goto :finish

:error
echo.
echo ERROR: Catalog update, commit, or push failed. Review the messages above.
set "EXIT_CODE=1"

:finish
pause
exit /b %EXIT_CODE%
