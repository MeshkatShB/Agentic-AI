"""Migration to create MCP servers table."""

import logging
from sqlalchemy import text
from backend.models.database import engine, Base
from backend.models.mcp_server import MCPServer

logger = logging.getLogger(__name__)


def migrate():
    """Create MCP servers table if it doesn't exist."""
    try:
        # Create table using SQLAlchemy
        MCPServer.__table__.create(bind=engine, checkfirst=True)
        logger.info("MCP servers table created successfully")
    except Exception as e:
        logger.error(f"Failed to create MCP servers table: {e}")
        raise

