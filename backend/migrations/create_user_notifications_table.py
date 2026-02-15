"""Migration to create user_notifications table."""

import logging
from backend.models.database import engine
from backend.models.user_notification import UserNotification

logger = logging.getLogger(__name__)


def migrate():
    """Create user_notifications table if it doesn't exist."""
    try:
        UserNotification.__table__.create(bind=engine, checkfirst=True)
        logger.info("user_notifications table created successfully")
    except Exception as e:
        logger.error(f"Failed to create user_notifications table: {e}")
        raise
