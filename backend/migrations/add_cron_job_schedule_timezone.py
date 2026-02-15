"""Add schedule_timezone column to cron_jobs."""

import logging
from sqlalchemy import text, inspect
from backend.models.database import engine

logger = logging.getLogger(__name__)


def migrate():
    """Add schedule_timezone if it doesn't exist."""
    insp = inspect(engine)
    cols = [c["name"] for c in insp.get_columns("cron_jobs")]
    if "schedule_timezone" in cols:
        logger.info("cron_jobs.schedule_timezone column already exists")
        return
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE cron_jobs ADD COLUMN schedule_timezone VARCHAR(64)"))
            conn.commit()
        logger.info("cron_jobs.schedule_timezone column added")
    except Exception as e:
        logger.error("Failed to add schedule_timezone: %s", e)
        raise
