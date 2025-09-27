"""Chat API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json
import asyncio

from backend.models import get_db, User, Conversation, Message, AgentStep
from backend.auth import get_current_user
from backend.agent import agent_executor
from backend.storage import get_vector_store

router = APIRouter()


class ConversationCreate(BaseModel):
    """Create conversation request."""
    title: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_steps: Optional[int] = 10


class ConversationResponse(BaseModel):
    """Conversation response."""
    id: int
    title: Optional[str]
    total_messages: int
    created_at: str
    updated_at: Optional[str]


class MessageRequest(BaseModel):
    """Message request."""
    content: str
    stream: bool = True
    selected_tools: Optional[List[str]] = []


class MessageResponse(BaseModel):
    """Message response."""
    id: int
    role: str
    content: str
    tool_name: Optional[str]
    tool_output: Optional[dict]
    created_at: str


@router.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    data: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new conversation."""
    
    conversation = Conversation(
        user_id=current_user.id,
        title=data.title or "New Conversation",
        model=data.model or current_user.preferences.get("model"),
        temperature=data.temperature,
        max_steps=data.max_steps
    )
    
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        total_messages=0,
        created_at=conversation.created_at.isoformat(),
        updated_at=None
    )


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20,
    offset: int = 0
):
    """List user's conversations."""
    
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id
    ).order_by(
        Conversation.updated_at.desc()
    ).limit(limit).offset(offset).all()
    
    return [
        ConversationResponse(
            id=conv.id,
            title=conv.title,
            total_messages=conv.total_messages,
            created_at=conv.created_at.isoformat(),
            updated_at=conv.updated_at.isoformat() if conv.updated_at else None
        )
        for conv in conversations
    ]


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get conversation details with messages."""
    
    # Get conversation
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Get messages
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()
    
    return {
        "conversation": conversation.to_dict(),
        "messages": [msg.to_dict() for msg in messages]
    }


@router.get("/conversations/{conversation_id}/steps")
async def get_conversation_steps(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed agent steps for a conversation."""
    
    # Verify conversation ownership
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Get agent steps
    agent_steps = db.query(AgentStep).filter(
        AgentStep.conversation_id == conversation_id
    ).order_by(AgentStep.step_number, AgentStep.created_at).all()
    
    return {
        "conversation_id": conversation_id,
        "steps": [step.to_dict() for step in agent_steps]
    }


@router.put("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    updates: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update conversation details."""
    
    # Get conversation
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Update allowed fields
    if "title" in updates:
        conversation.title = updates["title"]
    if "model" in updates:
        conversation.model = updates["model"]
    if "temperature" in updates:
        conversation.temperature = updates["temperature"]
    if "max_steps" in updates:
        conversation.max_steps = updates["max_steps"]
    
    # Update timestamp
    from datetime import datetime
    conversation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(conversation)
    
    # Get message count
    message_count = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).count()
    
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        total_messages=message_count,
        created_at=conversation.created_at.isoformat(),
        updated_at=conversation.updated_at.isoformat() if conversation.updated_at else None
    )


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: int,
    request: MessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to the conversation."""
    
    # Verify conversation ownership
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    async def generate():
        """Generate streaming response."""
        try:
            async for event in agent_executor.execute(
                user=current_user,
                conversation_id=conversation_id,
                message=request.content,
                db=db,
                stream=request.stream,
                selected_tools=request.selected_tools
            ):
                # Format as SSE
                if request.stream:
                    yield f"data: {json.dumps(event)}\n\n"
                else:
                    yield json.dumps(event)
        except Exception as e:
            error_event = {"type": "error", "error": str(e)}
            yield f"data: {json.dumps(error_event)}\n\n"
    
    if request.stream:
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )
    else:
        # For non-streaming, collect all events
        events = []
        async for event in generate():
            events.append(json.loads(event))
        return events[-1] if events else {"error": "No response generated"}


@router.post("/conversations/{conversation_id}/stop")
async def stop_generation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Stop the current generation for a conversation."""
    
    # Verify conversation ownership
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Stop the agent execution for this user
    agent_executor.clear_agent(current_user.id)
    
    return {"message": "Generation stopped successfully"}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a conversation."""
    
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Delete from vector store
    vector_store = get_vector_store()
    # Note: You'd need to track message IDs in vector store for this
    
    # Delete from database (cascade will delete messages)
    db.delete(conversation)
    db.commit()
    
    return {"message": "Conversation deleted successfully"}


@router.post("/conversations/{conversation_id}/search")
async def search_conversation(
    conversation_id: int,
    query: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 5
):
    """Search within a conversation."""
    
    # Verify conversation ownership
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Search in vector store
    vector_store = get_vector_store()
    results = await vector_store.search(
        query=query,
        k=limit,
        filter={"conversation_id": conversation_id},
        collection_name="conversations"
    )
    
    return {"results": results}


@router.post("/conversations/{conversation_id}/summarize")
async def summarize_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate a summary of the conversation."""
    
    # Verify conversation ownership
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    # Get all messages
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at).all()
    
    if not messages:
        return {"summary": "No messages to summarize"}
    
    # Create summary prompt
    conversation_text = "\n".join([
        f"{msg.role}: {msg.content[:500]}"
        for msg in messages[:20]  # Limit to first 20 messages
    ])
    
    # Use agent to generate summary
    summary_prompt = f"Summarize this conversation in 2-3 sentences:\n\n{conversation_text}"
    
    # Note: In production, you'd use the LLM directly for this
    # For now, return a placeholder
    summary = f"This conversation has {len(messages)} messages discussing various topics."
    
    # Update conversation summary
    conversation.summary = summary
    db.commit()
    
    return {"summary": summary}
