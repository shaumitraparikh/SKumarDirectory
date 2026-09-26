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
echo  UPDATE COMPLETE! 
echo  Your Search and Print HTML files are now up to date.
echo =======================================================
echo.
pause
