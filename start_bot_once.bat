@echo off
title Crypto Bot - Single Scan
color 0A
echo ========================================
echo   Crypto Bot - Single Scan
echo ========================================
echo.

cd /d "%~dp0"

echo Running one scan and exiting...
echo.

python main.py --once

echo.
echo Scan complete.
pause
