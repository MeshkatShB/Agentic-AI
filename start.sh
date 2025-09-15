#!/bin/bash

# Local AI Agent Startup Script

echo "🚀 Starting Local AI Agent..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env file with your configuration"
fi

# Check if Ollama is running
echo "🔍 Checking Ollama status..."
if curl -s http://127.0.0.1:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama is running"
else
    echo "❌ Ollama is not running. Please start Ollama first:"
    echo "   Visit: https://ollama.com/download"
    exit 1
fi

# Check if Qwen model is available
echo "🔍 Checking for Qwen model..."
if ollama list | grep -q "qwen"; then
    echo "✅ Qwen model found"
else
    echo "📦 Pulling Qwen model..."
    ollama pull qwen2.5:3b
fi

# Install backend dependencies
echo "📦 Installing backend dependencies..."
pip install -r requirements.txt

# Initialize database
echo "🗄️ Initializing database..."
python backend/init_db.py

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend
npm install
cd ..

# Start backend in background
echo "🚀 Starting backend server..."
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 5

# Start frontend
echo "🚀 Starting frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!

# Print success message
echo ""
echo "✨ Local AI Agent is running!"
echo ""
echo "🌐 Frontend: http://localhost:5173"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "📝 Default credentials:"
echo "   Admin: admin / admin123"
echo "   Demo: demo / demo123"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "echo '🛑 Stopping services...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
