"""Migration to create cron_jobs table."""

import logging
from backend.models.database import engine
from backend.models.cron_job import CronJob

logger = logging.getLogger(__name__)


def migrate():
    """Create cron_jobs table if it doesn't exist."""
    try:
        CronJob.__table__.create(bind=engine, checkfirst=True)
        logger.info("cron_jobs table created successfully")
    except Exception as e:
        logger.error(f"Failed to create cron_jobs table: {e}")
        raise
