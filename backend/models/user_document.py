"""User document model for storing user-uploaded files."""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from backend.models.database import Base


class UserDocument(Base):
    __tablename__ = "user_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # File information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)  # Path where file is stored
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_type = Column(String(50), nullable=False)  # MIME type or extension
    content_hash = Column(String(64), nullable=False)  # SHA-256 hash for deduplication
    
    # Indexing status
    is_indexed = Column(Integer, default=0)  # 0 = not indexed, 1 = indexed
    indexed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional metadata (renamed from 'metadata' to avoid SQLAlchemy conflict)
    document_metadata = Column(Text)  # JSON string with additional metadata
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", backref="documents")
    
    def to_dict(self):
        """Convert document to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "content_hash": self.content_hash,
            "is_indexed": bool(self.is_indexed),
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
            "document_metadata": self.document_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

