"""Run history for cron jobs (OpenClaw-style)."""

from sqlalchemy import Column, Integer, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
from backend.models.database import Base


class CronJobRun(Base):
    __tablename__ = "cron_job_runs"

    id = Column(Integer, primary_key=True, index=True)
    cron_job_id = Column(Integer, ForeignKey("cron_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    run_at = Column(DateTime(timezone=True), nullable=False)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    cron_job = relationship("CronJob", backref=backref("runs", cascade="all, delete-orphan"))
