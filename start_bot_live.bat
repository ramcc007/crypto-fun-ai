@echo off
title Crypto Bot — LIVE TRADING
color 0C
echo ========================================
echo   Crypto Bot — LIVE TRADING
echo   REAL MONEY on Binance
echo ========================================
echo.
echo  Starting bot...
echo  Open your browser at: http://localhost:5000
echo.
echo  Press Ctrl+C to stop.
echo.
cd /d "%~dp0"
python main.py --trade --live
pause
