@echo off
title Stock Dashboard

echo Starting backend...
start "Stock-Backend" cmd /c "cd /d C:\Users\Lzs\stock-dashboard\backend && python -m api"

echo Starting frontend...
start "Stock-Frontend" cmd /c "cd /d C:\Users\Lzs\stock-dashboard\frontend && npx vite --host 0.0.0.0 --port 5173"

echo.
echo Waiting for services...
timeout /t 6 /nobreak >nul

echo.
echo Opening browser...
start http://localhost:5173

echo.
echo System started! Close this window.
