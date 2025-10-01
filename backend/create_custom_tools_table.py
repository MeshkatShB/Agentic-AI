#!/usr/bin/env python3
"""Create custom_tools table."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import Base, engine, CustomTool
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_custom_tools_table():
    """Create the custom_tools table."""
    try:
        # Create all tables (this will only create missing ones)
        Base.metadata.create_all(bind=engine)
        logger.info("Custom tools table created successfully!")
        
        # Verify the table exists
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'custom_tools' in tables:
            logger.info("✅ custom_tools table exists")
            
            # Show table structure
            columns = inspector.get_columns('custom_tools')
            logger.info("Table structure:")
            for col in columns:
                logger.info(f"  - {col['name']}: {col['type']}")
        else:
            logger.error("❌ custom_tools table was not created")
            
    except Exception as e:
        logger.error(f"Error creating custom_tools table: {e}")
        raise

if __name__ == "__main__":
    create_custom_tools_table()
