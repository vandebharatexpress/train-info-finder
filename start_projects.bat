@echo off
title Train Info Finder Launcher

echo =====================================
echo       TRAIN INFO FINDER
echo =====================================
echo.

echo Starting Backend...
start "BACKEND" cmd /k "cd /d C:\Users\Armaan\Documents\train-info-finder\backend && call venv\Scripts\activate.bat && python -m uvicorn main:app --reload"

echo Starting Frontend...
start "FRONTEND" cmd /k "cd /d C:\Users\Armaan\Documents\train-info-finder\frontend && npm run dev"

echo.
echo Waiting for website to become ready...

powershell -NoProfile -ExecutionPolicy Bypass -Command "$url='http://localhost:5173'; for($i=0; $i -lt 30; $i++){ try { Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 1 | Out-Null; Start-Process $url; exit } catch { Start-Sleep -Seconds 1 } }; Start-Process $url"

echo.
echo Website opened!
pause