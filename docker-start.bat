@echo off
REM Quick start script for Docker deployment (Windows)

echo 🐳 Starting Local AI Agent with Docker...

REM Check if .env exists
if not exist .env (
    echo 📝 Creating .env file from template...
    copy env.example .env
    echo ⚠️  Please edit .env file with your configuration before continuing
    pause
)

REM Build and start services
REM Note: docker-compose up -d will build automatically if images don't exist
REM But we build explicitly to ensure fresh images
echo 🔨 Building Docker images (if needed)...
docker-compose build

echo 🚀 Starting services...
docker-compose up -d

echo ⏳ Waiting for services to be ready...
timeout /t 10 /nobreak >nul

REM Check service health
echo 🏥 Checking service health...
docker-compose ps

REM Pull Ollama model if needed (only when Ollama service is running)
echo.
echo 📦 Checking Ollama models...
docker-compose ps ollama 2>nul | findstr "Up" >nul
if not errorlevel 1 (
    docker-compose exec -T ollama ollama list 2>nul | findstr "qwen3" >nul
    if errorlevel 1 (
        echo 📥 Pulling qwen3:latest model (this may take a while)...
        docker-compose exec -T ollama ollama pull qwen3:latest
    ) else (
        echo ✅ Qwen3 model already available
    )
) else (
    echo ℹ️  Ollama not running in Docker. Use host's Ollama or start with: docker-compose --profile ollama-docker up -d
)

echo.
echo ✨ Local AI Agent is running!
echo.
echo 🌐 Frontend: http://localhost:8080
echo 🔧 Backend API: http://localhost:3333
echo 📚 API Docs: http://localhost:3333/docs
echo 🤖 Ollama: http://localhost:11434
echo.
echo 📝 Default credentials:
echo    Admin: admin / admin123
echo    Demo: demo / demo123
echo.
echo 📊 View logs: docker-compose logs -f
echo 🛑 Stop services: docker-compose down
echo.
pause

