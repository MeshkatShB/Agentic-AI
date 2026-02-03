"""Migration to create telegram_pairings table."""

import logging
from backend.models.database import engine, Base
from backend.models.telegram_pairing import TelegramPairing

logger = logging.getLogger(__name__)


def migrate():
    """Create telegram_pairings table if it doesn't exist."""
    try:
        TelegramPairing.__table__.create(bind=engine, checkfirst=True)
        logger.info("telegram_pairings table created successfully")
    except Exception as e:
        logger.error(f"Failed to create telegram_pairings table: {e}")
        raise
