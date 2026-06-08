@echo off
title Crypto Bot — Single Scan
color 0A
echo ========================================
echo   Crypto Bot — Single Scan (Alert Only)
echo ========================================
echo.
cd /d "%~dp0"
python main.py --once
echo.
pause
