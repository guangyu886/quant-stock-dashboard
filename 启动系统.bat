@echo off
chcp 65001 >nul 2>&1
title 量化投研系统

echo ========================================
echo   量化投研系统 - 一键启动
echo ========================================
echo.

cd /d "C:\Users\Lzs\stock-dashboard\backend"

echo [1/3] 检查依赖...
pip install -q akshare yfinance pandas fastapi uvicorn apscheduler 2>nul

echo [2/3] 启动后端服务...
start "量化投研-后端" cmd /c "cd /d C:\Users\Lzs\stock-dashboard\backend && python -m api"

echo [3/3] 启动前端服务...
start "量化投研-前端" cmd /c "cd /d C:\Users\Lzs\stock-dashboard\frontend && npm install --silent 2>nul && npx vite --host 0.0.0.0 --port 5173"

timeout /t 6 >nul

echo.
echo ========================================
echo   启动完成!
echo   后端: http://localhost:8000
echo   前端: http://localhost:5173
echo ========================================
echo.
echo   按任意键打开浏览器...
pause >nul
start http://localhost:5173
