@echo off
REM POE2 Analytics — Startup Script
cd /d E:\project-poe2
echo Starting POE2 Analytics...
echo.
echo Web UI: http://127.0.0.1:8002
echo API:    http://127.0.0.1:8002/docs
echo.
"C:\Users\pc\AppData\Local\Programs\Python\Python312\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8006 --reload
pause
