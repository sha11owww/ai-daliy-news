@echo off
title AI Daily

echo [1/3] Starting API...
start "API" /B uvicorn api.main:app --reload --port 8000 > api.log 2>&1
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
echo API      : http://localhost:8000
echo.
echo Tips:
echo - 今日无数据是正常的，等 7:00 早报生成
echo - 点击左边日历可看 5月6日 历史数据
echo ====================
echo.
pause
