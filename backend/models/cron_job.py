"""CronJob model for scheduled background jobs created by the chatbot."""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.models.database import Base


class CronJob(Base):
    __tablename__ = "cron_jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    job_type = Column(String(50), nullable=False, index=True)  # e.g. reminder, notification
    next_run_at = Column(DateTime(timezone=True), nullable=False, index=True)
    cron_expression = Column(String(100), nullable=True)  # 5-field cron e.g. "0 7 * * *"; if set, recurring
    schedule_timezone = Column(String(64), nullable=True)  # IANA e.g. "America/Los_Angeles"; default UTC
    payload = Column(JSON, nullable=True)  # type-specific data, e.g. {"body": "..."} for reminder
    status = Column(String(20), nullable=False, default="scheduled", index=True)  # scheduled, running, completed, failed, cancelled
    source = Column(String(20), nullable=False, default="chat")  # chat, telegram, ui
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    user = relationship("User", backref="cron_jobs")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "job_type": self.job_type,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "cron_expression": self.cron_expression,
            "schedule_timezone": self.schedule_timezone,
            "payload": self.payload,
            "status": self.status,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }
