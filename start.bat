@echo off
title Local AI Agent

echo Starting Local AI Agent...
echo.

:: Check if .env file exists
if not exist .env (
    echo Creating .env file from template...
    copy env.example .env
    echo Please edit .env file with your configuration
    echo.
)

:: Check if Ollama is running
echo Checking Ollama status...
curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo Ollama is running
) else (
    echo Ollama is not running. Please start Ollama first:
    echo Visit: https://ollama.com/download
    pause
    exit /b 1
)

:: Check if Qwen model is available
echo Checking for Qwen model...
ollama list | findstr "qwen" >nul 2>&1
if %errorlevel% equ 0 (
    echo Qwen model found
) else (
    echo Pulling Qwen model...
    ollama pull qwen2.5:3b
)

:: Install backend dependencies
echo Installing backend dependencies...
pip install -r requirements.txt

:: Initialize database
echo Initializing database...
python backend\init_db.py

:: Install frontend dependencies
echo Installing frontend dependencies...
cd frontend
call npm install
cd ..

:: Start backend in new window
echo Starting backend server...
start "Backend Server" cmd /k "uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"

:: Wait for backend to start
echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

:: Start frontend in new window
echo Starting frontend...
cd frontend
start "Frontend Server" cmd /k "npm run dev"
cd ..

:: Print success message
echo.
echo =====================================
echo    Local AI Agent is running!
echo =====================================
echo.
echo Frontend: http://localhost:5173
echo Backend API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo Default credentials:
echo   Admin: admin / admin123
echo   Demo: demo / demo123
echo.
echo Close this window to keep services running
echo or press any key to stop all services
echo.
pause

:: Kill services
taskkill /FI "WindowTitle eq Backend Server*" /T /F >nul 2>&1
taskkill /FI "WindowTitle eq Frontend Server*" /T /F >nul 2>&1
