@echo off
title SharpStack Analytics

cd /d "%~dp0"

echo.
echo ==========================================
echo        SharpStack Analytics
echo ==========================================
echo.

python build.py --launch

pause
