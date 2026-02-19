#!/bin/bash
# Quick start script for Docker deployment

set -e

echo "🐳 Starting Local AI Agent with Docker..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env file with your configuration before continuing"
    echo "   Press Enter to continue or Ctrl+C to exit..."
    read
fi

# Build and start services
# Note: docker-compose up -d will build automatically if images don't exist
# But we build explicitly to ensure fresh images
echo "🔨 Building Docker images (if needed)..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🏥 Checking service health..."
docker-compose ps

# Pull Ollama model if needed (only when Ollama service is running)
echo ""
echo "📦 Checking Ollama models..."
if docker-compose ps ollama 2>/dev/null | grep -q "Up"; then
    if ! docker-compose exec -T ollama ollama list 2>/dev/null | grep -q "qwen3"; then
        echo "📥 Pulling qwen3:latest model (this may take a while)..."
        docker-compose exec -T ollama ollama pull qwen3:latest
    else
        echo "✅ Qwen3 model already available"
    fi
else
    echo "ℹ️  Ollama not running in Docker (using host's Ollama or start with: docker-compose --profile ollama-docker up -d)"
fi

echo ""
echo "✨ Local AI Agent is running!"
echo ""
echo "🌐 Frontend: http://localhost:8080"
echo "🔧 Backend API: http://localhost:3333"
echo "📚 API Docs: http://localhost:3333/docs"
echo "🤖 Ollama: http://localhost:11434"
echo ""
echo "📝 Default credentials:"
echo "   Admin: admin / admin123"
echo "   Demo: demo / demo123"
echo ""
echo "📊 View logs: docker-compose logs -f"
echo "🛑 Stop services: docker-compose down"
echo ""

