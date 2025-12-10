"""Migration script to add file_attachments column to messages table."""

import sys
from pathlib import Path
import logging

# Add the parent directory to Python path
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from sqlalchemy import text, inspect
from backend.models.database import engine, SessionLocal

logger = logging.getLogger(__name__)


def migrate():
    """Add file_attachments column to messages table if it doesn't exist."""
    
    print("Starting migration: Add file_attachments column to messages table")
    logger.info("Starting migration: Add file_attachments column to messages table")
    
    db = SessionLocal()
    try:
        # Check if column already exists
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('messages')]
        
        if 'file_attachments' in columns:
            print("✓ Column 'file_attachments' already exists. Migration not needed.")
            logger.info("Column 'file_attachments' already exists. Migration not needed.")
            return
        
        # Add the column
        print("Adding 'file_attachments' column to messages table...")
        logger.info("Adding 'file_attachments' column to messages table...")
        db.execute(text("ALTER TABLE messages ADD COLUMN file_attachments JSON"))
        db.commit()
        
        print("✓ Successfully added 'file_attachments' column to messages table")
        logger.info("✓ Successfully added 'file_attachments' column to messages table")
        
    except Exception as e:
        db.rollback()
        print(f"✗ Migration failed: {e}")
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()

