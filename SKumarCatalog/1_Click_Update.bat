@echo off
title Catalog Builder Update
color 0A
echo =======================================================
echo         S. KUMAR & BROS - CATALOG UPDATER
echo =======================================================
echo.
echo Rebuilding your catalogs from the latest CSV data...
echo.

:: Switch to the directory where this batch file is located
cd /d "%~dp0"

:: Run the python script
python build_catalog.py

echo.
echo =======================================================
echo  UPDATING WEBSITE (GITHUB)...
echo =======================================================
:: Go up one directory to the root of the git repo
cd ..
git add .
git commit -m "Auto-update catalog data"
git push

echo.
echo =======================================================
echo  UPDATE COMPLETE! 
echo  Your Search and Print HTML files are now up to date.
echo  The live website will refresh in 1-2 minutes.
echo =======================================================
echo.
pause
