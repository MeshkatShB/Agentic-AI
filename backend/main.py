"""Main FastAPI application."""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import asyncio

from backend.config import settings
from backend.models import Base, engine, get_db, User, Conversation, Message
from backend.auth import authenticate_user, create_access_token, get_current_user, get_password_hash
from backend.agent import agent_executor
from backend.storage import get_vector_store
from backend.api import auth_router, chat_router, tools_router, settings_router

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
app.include_router(settings_router, prefix="/api/settings", tags=["Settings"])


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
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
        reload=True
    )
