"""Migration to create cron_job_runs table (run history)."""

import logging
from backend.models.database import engine
from backend.models.cron_job_run import CronJobRun

logger = logging.getLogger(__name__)


def migrate():
    """Create cron_job_runs table if it doesn't exist."""
    try:
        CronJobRun.__table__.create(bind=engine, checkfirst=True)
        logger.info("cron_job_runs table created successfully")
    except Exception as e:
        logger.error("Failed to create cron_job_runs table: %s", e)
        raise
