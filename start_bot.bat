@echo off
title Crypto Bot — Dry Run Auto-Trade
color 0A
echo ========================================
echo   Crypto Bot — Auto-Trade (DRY RUN)
echo   Simulates trades. No real money.
echo ========================================
echo.
cd /d "%~dp0"
python main.py --trade
pause
