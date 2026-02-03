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
import logging
from pathlib import Path

from backend.config import settings

# Create logs directory if it doesn't exist
logs_dir = Path('logs')
logs_dir.mkdir(exist_ok=True)

# Configure logging
handlers = [
    logging.StreamHandler(),  # Console output
    logging.FileHandler('logs/app.log', encoding='utf-8', mode='a')  # File output
]

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=handlers
)

# Set log levels for specific modules
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
# Suppress ChromaDB telemetry errors
logging.getLogger("chromadb.telemetry").setLevel(logging.ERROR)
# Suppress cryptography deprecation warnings
logging.getLogger("pypdf._crypt_providers._cryptography").setLevel(logging.ERROR)
# Suppress passlib/bcrypt version warning
logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="cryptography")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pypdf")

logger = logging.getLogger(__name__)
from backend.models import Base, engine, get_db, User, Conversation, Message
from backend.auth import authenticate_user, create_access_token, get_current_user, get_password_hash
from backend.agent import agent_executor
from backend.storage import get_vector_store
from backend.api import auth_router, chat_router, tools_router, settings_router, custom_tools_router, documents_router, browser_use_router, mcp_router

# Create database tables
Base.metadata.create_all(bind=engine)

# Run migrations
try:
    from backend.migrations.add_file_attachments_column import migrate as migrate_file_attachments
    migrate_file_attachments()
except Exception as e:
    logger.warning(f"Migration check failed (this is OK if column already exists): {e}")

try:
    from backend.migrations.create_mcp_servers_table import migrate as migrate_mcp_servers
    migrate_mcp_servers()
except Exception as e:
    logger.warning(f"MCP servers table migration check failed (this is OK if table already exists): {e}")

try:
    from backend.migrations.add_last_tool_count_column import migrate as migrate_tool_count
    migrate_tool_count()
except Exception as e:
    logger.warning(f"last_tool_count column migration check failed (this is OK if column already exists): {e}")

try:
    from backend.migrations.create_telegram_pairing_table import migrate as migrate_telegram_pairing
    migrate_telegram_pairing()
except Exception as e:
    logger.warning(f"Telegram pairings table migration check failed (this is OK if table already exists): {e}")

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Local-first AI Agent with privacy-preserving features"
)

# Configure CORS
# Handle Chrome extension origins (chrome-extension://) and regular origins
def get_cors_origins():
    """Get CORS origins, handling Chrome extension protocol."""
    origins = []
    for origin in settings.CORS_ORIGINS:
        if origin == "*":
            return ["*"]  # Allow all origins
        origins.append(origin)
    
    # Chrome extensions use chrome-extension:// protocol
    # We need to allow all chrome-extension origins or use a wildcard
    # For security, we'll check if any origin contains chrome-extension
    # If CORS_ORIGINS includes "*", allow all
    return origins

# Use allow_origin_regex for Chrome extensions if needed
cors_origins = get_cors_origins()
allow_all = "*" in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if not allow_all else ["*"],
    allow_origin_regex=r"^chrome-extension://.*" if not allow_all else None,  # Allow all Chrome extensions
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
app.include_router(documents_router, prefix="/api/documents", tags=["Documents"])
app.include_router(browser_use_router, prefix="/api/browser-use", tags=["Browser Use"])
app.include_router(mcp_router, prefix="/api/mcp", tags=["MCP Servers"])


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
    
    # Start Telegram bot if configured
    if getattr(settings, "ENABLE_TELEGRAM_BOT", False) and (getattr(settings, "TELEGRAM_BOT_TOKEN", None) or "").strip():
        try:
            from backend.services.telegram_bot import start_telegram_bot
            await start_telegram_bot()
        except Exception as e:
            logger.warning(f"Telegram bot failed to start: {e}")
    
    # Log startup
    logger.info(f"{settings.APP_NAME} v{settings.APP_VERSION} started")
    logger.info(f"Using model: {settings.DEFAULT_MODEL}")
    logger.info(f"Vector store: {settings.VECTOR_STORE}")
    logger.info(f"Logging level: {'DEBUG' if settings.DEBUG else 'INFO'}")
    logger.info("Logs are being written to console and logs/app.log")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    # Stop Telegram bot
    try:
        from backend.services.telegram_bot import stop_telegram_bot
        await stop_telegram_bot()
    except Exception as e:
        logger.warning(f"Telegram bot shutdown: {e}")
    
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
