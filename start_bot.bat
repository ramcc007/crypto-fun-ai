@echo off
title Crypto Opportunity Bot
color 0A
echo ========================================
echo   Crypto SPOT Opportunity Bot
echo ========================================
echo.

cd /d "%~dp0"

echo Starting continuous scan (every 5 minutes)...
echo Press Ctrl+C to stop.
echo.

python main.py

pause
