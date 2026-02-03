"""Migration to add last_tool_count column to mcp_servers table."""

import logging
from sqlalchemy import text, inspect
from backend.models.database import engine

logger = logging.getLogger(__name__)


def migrate():
    """Add last_tool_count column to mcp_servers table if it doesn't exist."""
    try:
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('mcp_servers')]
        
        if 'last_tool_count' not in columns:
            with engine.connect() as conn:
                conn.execute(text("""
                    ALTER TABLE mcp_servers 
                    ADD COLUMN last_tool_count INTEGER
                """))
                conn.commit()
                logger.info("Added last_tool_count column to mcp_servers table")
        else:
            logger.info("Column last_tool_count already exists")
    except Exception as e:
        logger.error(f"Failed to add last_tool_count column: {e}")
        raise

