"""In-app notifications (e.g. delivered reminders)."""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.models.database import Base


class UserNotification(Base):
    __tablename__ = "user_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    body = Column(Text, nullable=True)
    cron_job_id = Column(Integer, ForeignKey("cron_jobs.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    read_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", backref="notifications")
