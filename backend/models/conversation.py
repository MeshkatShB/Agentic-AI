"""Conversation and message models."""

from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.models.database import Base


class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200))
    summary = Column(Text)
    
    # Agent settings for this conversation
    model = Column(String(100))
    temperature = Column(Float)
    max_steps = Column(Integer)
    
    # Metadata
    total_messages = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    agent_steps = relationship("AgentStep", back_populates="conversation", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert conversation to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "summary": self.summary,
            "model": self.model,
            "total_messages": self.total_messages,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # "user", "assistant", "system", "tool"
    content = Column(Text, nullable=False)
    
    # For tool messages
    tool_name = Column(String(100))
    tool_input = Column(JSON)
    tool_output = Column(JSON)
    tool_approved = Column(Integer)  # 1 = approved, 0 = denied, null = no approval needed
    
    # Agent reasoning (for assistant messages)
    reasoning = Column(Text)
    plan = Column(Text)
    step_number = Column(Integer)
    
    # Metadata
    tokens_used = Column(Integer)
    embedding_id = Column(String(100))  # ID in vector store
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    def to_dict(self):
        """Convert message to dictionary."""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_output": self.tool_output,
            "tool_approved": self.tool_approved,
            "reasoning": self.reasoning,
            "plan": self.plan,
            "step_number": self.step_number,
            "tokens_used": self.tokens_used,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class AgentStep(Base):
    """Model for storing detailed agent execution steps."""
    __tablename__ = "agent_steps"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"), nullable=True, index=True)
    
    # Step details
    step_type = Column(String(50), nullable=False)  # "thinking", "tool_request", "tool_result", "reflection"
    step_number = Column(Integer, nullable=False)
    title = Column(String(200))
    content = Column(Text)
    
    # Tool-specific fields
    tool_name = Column(String(100))
    tool_input = Column(JSON)
    tool_output = Column(JSON)
    tool_success = Column(Boolean)
    tool_error = Column(Text)
    
    # Execution metadata
    execution_time = Column(Float)  # Time taken for this step in seconds
    tokens_used = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    conversation = relationship("Conversation", back_populates="agent_steps")
    message = relationship("Message")
    
    def to_dict(self):
        """Convert agent step to dictionary."""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "message_id": self.message_id,
            "step_type": self.step_type,
            "step_number": self.step_number,
            "title": self.title,
            "content": self.content,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_output": self.tool_output,
            "tool_success": self.tool_success,
            "tool_error": self.tool_error,
            "execution_time": self.execution_time,
            "tokens_used": self.tokens_used,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
