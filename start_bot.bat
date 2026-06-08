@echo off
title Crypto Bot — Dry Run
color 0A
echo ========================================
echo   Crypto Bot — DRY RUN + Dashboard
echo ========================================
echo.
echo  Starting bot...
echo  Open your browser at: http://localhost:5000
echo.
echo  Press Ctrl+C to stop.
echo.
cd /d "%~dp0"
python main.py --trade
pause
