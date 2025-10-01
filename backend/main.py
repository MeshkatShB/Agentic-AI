"""Main FastAPI application."""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import asyncio
import time

from backend.config import settings
from backend.models import Base, engine, get_db, User, Conversation, Message
from backend.auth import authenticate_user, create_access_token, get_current_user, get_password_hash
from backend.agent import agent_executor
from backend.storage import get_vector_store
from backend.api import auth_router, chat_router, tools_router, settings_router, custom_tools_router

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Local-first AI Agent with privacy-preserving features"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(chat_router, prefix="/api/chat", tags=["Chat"])
app.include_router(tools_router, prefix="/api/tools", tags=["Tools"])
app.include_router(custom_tools_router, prefix="/api/custom-tools", tags=["Custom Tools"])
app.include_router(settings_router, prefix="/api/settings", tags=["Settings"])


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    from datetime import datetime
    import psutil
    import os
    
    # Basic health info
    health_data = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.APP_VERSION,
        "uptime": time.time() - start_time if 'start_time' in globals() else 0
    }
    
    # System metrics (if psutil is available)
    try:
        process = psutil.Process()
        health_data["system"] = {
            "cpu_percent": process.cpu_percent(),
            "memory_mb": process.memory_info().rss / 1024 / 1024,
            "open_files": len(process.open_files()),
            "threads": process.num_threads()
        }
    except ImportError:
        health_data["system"] = {"status": "psutil not available"}
    
    # Database health
    try:
        db = next(get_db())
        db.execute(text("SELECT 1"))
        health_data["database"] = {"status": "connected"}
        db.close()
    except Exception as e:
        health_data["database"] = {"status": "error", "error": str(e)}
    
    return health_data


@app.get("/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    """Get application metrics."""
    from sqlalchemy import text
    
    metrics = {}
    
    try:
        # User metrics
        result = db.execute(text("SELECT COUNT(*) as count FROM users")).fetchone()
        metrics["users_total"] = result.count
        
        # Conversation metrics
        result = db.execute(text("SELECT COUNT(*) as count FROM conversations")).fetchone()
        metrics["conversations_total"] = result.count
        
        # Message metrics
        result = db.execute(text("SELECT COUNT(*) as count FROM messages")).fetchone()
        metrics["messages_total"] = result.count
        
        # Recent activity (last 24 hours)
        result = db.execute(text("""
            SELECT COUNT(*) as count FROM messages 
            WHERE created_at > datetime('now', '-1 day')
        """)).fetchone()
        metrics["messages_24h"] = result.count
        
        # Tool usage from agent_steps
        try:
            result = db.execute(text("""
                SELECT tool_name, COUNT(*) as count 
                FROM agent_steps 
                WHERE tool_name IS NOT NULL 
                GROUP BY tool_name
            """)).fetchall()
            metrics["tool_usage"] = {row.tool_name: row.count for row in result}
        except:
            metrics["tool_usage"] = {"error": "agent_steps table not available"}
        
    except Exception as e:
        metrics["error"] = str(e)
    
    return metrics


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global start_time
    start_time = time.time()
    
    # Initialize vector store
    vector_store = get_vector_store()
    await vector_store.initialize()
    
    # Log startup
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} started")
    logger.info(f"Using model: {settings.DEFAULT_MODEL}")
    logger.info(f"Vector store: {settings.VECTOR_STORE}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    # Clear all agents
    agent_executor.clear_all_agents()
    
    # Close LLM clients
    # (cleanup code here if needed)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model": settings.DEFAULT_MODEL,
        "vector_store": settings.VECTOR_STORE
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
