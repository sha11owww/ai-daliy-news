@echo off
title AI Daily

echo [sync] Pulling latest data from GitHub...
cd /d "%~dp0"
git pull origin main >nul 2>&1

echo [1/3] Starting API...
start "API" /B uvicorn api.main:app --reload --port 8001 > api.log 2>&1
timeout /t 4 >nul

echo [2/3] Starting Frontend...
cd /d "%~dp0frontend"
start "Frontend" /B npx vite --port 5173 > ..\frontend.log 2>&1
cd /d "%~dp0"
timeout /t 6 >nul

echo [3/3] Opening Browser...
start http://localhost:5173

echo.
echo ===== AI Daily =====
echo Frontend : http://localhost:5173
echo API      : http://localhost:8001
echo ====================
echo.
pause
