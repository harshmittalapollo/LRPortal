@echo off
cd /d "%~dp0"
set LRPORTAL_DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/lrportal
if "%BACKEND_PORT%"=="" set BACKEND_PORT=8002
echo Starting backend on port %BACKEND_PORT%...
"C:\Users\Harsh Mittal\.vscode\venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port %BACKEND_PORT% --reload
