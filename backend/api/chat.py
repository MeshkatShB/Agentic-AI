"""Chat API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
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
from backend.utils.file_parser import extract_file_content

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
    use_deepagent: bool = False
    file_contents: Optional[List[dict]] = []  # List of {filename, content, metadata}
    file_attachments: Optional[List[dict]] = []  # List of {filename, size, type} for tracking


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
        model=data.model or (current_user.preferences or {}).get("model"),
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
    
    # Security: Get messages, explicitly joining with Conversation to ensure user ownership
    # Filter out step messages (those with tool_name) - they're stored in AgentStep table
    # Only show actual chat messages (user messages and final assistant responses)
    messages = db.query(Message).join(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,  # Explicit user ownership check
        Message.conversation_id == conversation_id,
        Message.tool_name.is_(None)  # Exclude step messages that have tool_name set
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
    
    # Security: Get message count, explicitly joining with Conversation to ensure user ownership
    message_count = db.query(Message).join(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,  # Explicit user ownership check
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
    """Send a message to the conversation.
    
    Security: Verifies that the conversation belongs to the current user
    to prevent unauthorized access to other users' conversations and files.
    """
    
    # Security: Verify conversation ownership to prevent data breach
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id  # Explicit user ownership check
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied"
        )
    
    # Build message content with file contents appended
    message_content = request.content
    file_attachments_data = []
    file_sections = []  # Initialize to avoid UnboundLocalError
    
    if request.file_contents:
        for file_data in request.file_contents:
            filename = file_data.get("filename", "Unknown")
            content = file_data.get("content", "")
            metadata = file_data.get("metadata", {})
            
            if content:
                file_sections.append(f"\n\n--- Content from file: {filename} ---\n{content}\n--- End of file: {filename} ---")
            
            # Store file attachment metadata
            file_attachments_data.append({
                "filename": filename,
                "size": metadata.get("file_size", 0),
                "type": metadata.get("file_type", "unknown")
            })
    
    # Use file_attachments from request if provided (for tracking)
    if request.file_attachments:
        file_attachments_data = request.file_attachments
        
    # Append file sections to message content if any files were provided
    if file_sections:
        message_content = request.content + "\n\n" + "\n".join(file_sections)
    
    async def generate():
        """Generate streaming response."""
        try:
            async for event in agent_executor.execute(
                user=current_user,
                conversation_id=conversation_id,
                message=message_content,
                db=db,
                stream=request.stream,
                selected_tools=request.selected_tools,
                use_deepagent=request.use_deepagent,
                file_attachments=file_attachments_data if file_attachments_data else None
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


@router.post("/conversations/{conversation_id}/upload")
async def upload_file(
    conversation_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload and parse a file for the conversation.
    
    Security: Verifies that the conversation belongs to the current user
    to prevent unauthorized file uploads to other users' conversations.
    """
    
    # Security: Verify conversation ownership to prevent data breach
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id  # Explicit user ownership check
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied"
        )
    
    # Check file size (max 10MB)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    file_content = await file.read()
    
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    
    try:
        # Extract content from file
        content, metadata = await extract_file_content(
            file_content,
            file.filename,
            extract_metadata=True
        )
        
        return {
            "filename": file.filename,
            "content": content,
            "metadata": metadata,
            "success": True
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse file: {str(e)}"
        )


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
    
    # Security: Get all messages, explicitly joining with Conversation to ensure user ownership
    messages = db.query(Message).join(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,  # Explicit user ownership check
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


@router.get("/conversations/{conversation_id}/files")
async def get_conversation_files(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all files attached to messages in the conversation.
    
    Security: Verifies that the conversation belongs to the current user
    and only returns files from messages in that user's conversation
    to prevent unauthorized access to other users' files.
    """
    
    # Security: Verify conversation ownership to prevent data breach
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id  # Explicit user ownership check
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied"
        )
    
    # Security: Get messages with file attachments, explicitly joining with Conversation
    # to ensure we only get files from the authenticated user's conversation
    messages = db.query(Message).join(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,  # Explicit user ownership check
        Message.conversation_id == conversation_id,
        Message.file_attachments.isnot(None)
    ).order_by(Message.created_at).all()
    
    # Collect unique files (by filename and size to avoid duplicates)
    files_map = {}
    for msg in messages:
        if msg.file_attachments:
            for file_att in msg.file_attachments:
                file_key = f"{file_att.get('filename')}_{file_att.get('size')}"
                if file_key not in files_map:
                    files_map[file_key] = {
                        "filename": file_att.get("filename", "Unknown"),
                        "size": file_att.get("size", 0),
                        "type": file_att.get("type", "unknown"),
                        "message_id": msg.id,
                        "attached_at": msg.created_at.isoformat() if msg.created_at else None
                    }
    
    return {"files": list(files_map.values())}


@router.delete("/conversations/{conversation_id}/files/{message_id}")
async def delete_file_attachment(
    conversation_id: int,
    message_id: int,
    filename: str = Query(..., description="Name of the file to remove"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a file attachment from a message.
    
    Security: Verifies that both the conversation and message belong to the current user
    to prevent unauthorized deletion of other users' file attachments.
    """
    
    # Security: Verify conversation ownership to prevent data breach
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id  # Explicit user ownership check
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied"
        )
    
    # Security: Get the message and verify it belongs to the user's conversation
    # Explicitly join with Conversation to ensure user ownership at the database level
    message = db.query(Message).join(Conversation).filter(
        Message.id == message_id,
        Message.conversation_id == conversation_id,
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id  # Explicit user ownership check
    ).first()
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found or access denied"
        )
    
    # Remove the file from attachments
    if message.file_attachments:
        updated_attachments = [
            att for att in message.file_attachments
            if att.get("filename") != filename
        ]
        message.file_attachments = updated_attachments if updated_attachments else None
        db.commit()
    
    return {"message": "File attachment removed successfully"}
