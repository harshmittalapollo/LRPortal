@echo off
cd /d "%~dp0"
if "%FRONTEND_PORT%"=="" set FRONTEND_PORT=3001
set PORT=%FRONTEND_PORT%
set REACT_APP_API_URL=http://127.0.0.1:8002
"C:\Program Files\nodejs\npm.cmd" start
