"""Telegram pairing model - links app users to Telegram accounts via pairing code."""

from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.models.database import Base


class TelegramPairing(Base):
    __tablename__ = "telegram_pairings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    pairing_code = Column(String(12), nullable=False, index=True)  # e.g. 6–8 alphanumeric
    telegram_user_id = Column(BigInteger, nullable=True, unique=True, index=True)  # Set when paired
    telegram_username = Column(String(100), nullable=True)  # Telegram @username
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paired_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="telegram_pairing")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "pairing_code": self.pairing_code,
            "telegram_user_id": self.telegram_user_id,
            "telegram_username": self.telegram_username,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "paired_at": self.paired_at.isoformat() if self.paired_at else None,
        }
