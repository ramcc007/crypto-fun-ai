@echo off
title Crypto Bot — LIVE TRADING
color 0C
echo ========================================
echo   Crypto Bot — LIVE TRADING
echo   REAL MONEY — Real orders on Binance
echo ========================================
echo.
echo Press Ctrl+C at any time to stop.
echo.
cd /d "%~dp0"
python main.py --trade --live
pause
