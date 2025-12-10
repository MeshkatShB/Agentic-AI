"""Documents API endpoints for user file management."""

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from pathlib import Path
import hashlib
import asyncio
import logging
from datetime import datetime

from backend.models import get_db, User, UserDocument, SessionLocal
from backend.auth import get_current_user
from backend.storage import get_vector_store
from backend.config import settings

# LangChain document loaders
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Try to import UnstructuredHTMLLoader, fallback to BeautifulSoup if not available
try:
    from langchain_community.document_loaders import UnstructuredHTMLLoader
    HAS_UNSTRUCTURED = True
except ImportError:
    HAS_UNSTRUCTURED = False
    # Fallback: use BeautifulSoup for HTML parsing
    from bs4 import BeautifulSoup

router = APIRouter()
logger = logging.getLogger(__name__)

# Supported file types
SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.txt', '.md', '.html']
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class DocumentResponse(BaseModel):
    """Document response model."""
    id: int
    filename: str
    original_filename: str
    file_size: int
    file_type: str
    is_indexed: bool
    indexed_at: Optional[str]
    created_at: str


def get_user_documents_dir(user_id: int) -> Path:
    """Get the directory for storing user documents."""
    docs_dir = Path("user_documents") / str(user_id)
    docs_dir.mkdir(parents=True, exist_ok=True)
    return docs_dir


def calculate_file_hash(file_content: bytes) -> str:
    """Calculate SHA-256 hash of file content."""
    return hashlib.sha256(file_content).hexdigest()


def load_document_with_langchain(file_path: Path, file_type: str):
    """Load document using LangChain loaders."""
    file_ext = file_path.suffix.lower()
    
    try:
        if file_ext == '.pdf':
            loader = PyPDFLoader(str(file_path))
        elif file_ext == '.docx':
            loader = Docx2txtLoader(str(file_path))
        elif file_ext in ['.txt', '.md']:
            loader = TextLoader(str(file_path), encoding='utf-8')
        elif file_ext == '.html':
            if HAS_UNSTRUCTURED:
                loader = UnstructuredHTMLLoader(str(file_path))
            else:
                # Fallback: use BeautifulSoup to extract text from HTML
                from langchain_core.documents import Document
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    html_content = f.read()
                soup = BeautifulSoup(html_content, 'html.parser')
                text = soup.get_text(separator=' ', strip=True)
                docs = [Document(page_content=text, metadata={"source": str(file_path)})]
                return docs
        else:
            # Fallback to text loader
            loader = TextLoader(str(file_path), encoding='utf-8')
        
        # Load documents
        docs = loader.load()
        return docs
    except Exception as e:
        logger.error(f"Failed to load document {file_path} with LangChain: {e}")
        raise


async def index_user_document(
    document_id: int,
    file_path: Path,
    vector_store
):
    """Index a user document to the vector store using LangChain."""
    # Create a new database session for this background task
    db = SessionLocal()
    try:
        # Reload the document to ensure we have a fresh reference
        document = db.query(UserDocument).filter(UserDocument.id == document_id).first()
        if not document:
            logger.error(f"Document {document_id} not found for indexing")
            return False
        
        # Get user's embedding model preference
        from backend.models import User
        user = db.query(User).filter(User.id == document.user_id).first()
        embedding_model = None
        if user and user.preferences:
            embedding_model = user.preferences.get("embedding_model")
        
        # Load document using LangChain
        docs = await asyncio.to_thread(
            load_document_with_langchain, 
            file_path, 
            document.file_type
        )
        
        if not docs:
            logger.warning(f"No content extracted from {file_path}")
            return False
        
        # Get user-specific collection name
        collection_name = f"user_documents_{document.user_id}"
        
        # Use LangChain's RecursiveCharacterTextSplitter for chunking
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            length_function=len,
        )
        
        # Split documents into chunks
        chunks = text_splitter.split_documents(docs)
        
        if not chunks:
            logger.warning(f"No chunks created from {file_path}")
            return False
        
        # Prepare documents and metadata for vector store
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"doc_{document.id}_chunk_{i}"
            documents.append(chunk.page_content)
            
            # Merge chunk metadata with document metadata
            chunk_metadata = {
                "document_id": document.id,
                "user_id": document.user_id,
                "file_name": document.original_filename,
                "file_path": str(file_path),
                "file_type": document.file_type,
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            # Add any metadata from LangChain document
            if chunk.metadata:
                chunk_metadata.update(chunk.metadata)
            
            metadatas.append(chunk_metadata)
            ids.append(chunk_id)
        
        # Add to vector store with user's embedding model
        await vector_store.add_documents(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            collection_name=collection_name,
            embedding_model=embedding_model
        )
        
        # Update document status
        document.is_indexed = 1
        document.indexed_at = datetime.utcnow()
        db.commit()
        db.refresh(document)  # Refresh to ensure changes are visible
        
        logger.info(f"Successfully indexed document {document.id} with {len(chunks)} chunks")
        return True
        
    except Exception as e:
        logger.error(f"Failed to index document {document_id}: {e}", exc_info=True)
        return False
    finally:
        db.close()


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a document for the current user."""
    
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Supported types: {', '.join(SUPPORTED_EXTENSIONS)}"
        )
    
    # Read file content
    file_content = await file.read()
    
    # Check file size
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    
    # Calculate file hash
    content_hash = calculate_file_hash(file_content)
    
    # Check if file already exists (by hash)
    existing_doc = db.query(UserDocument).filter(
        UserDocument.user_id == current_user.id,
        UserDocument.content_hash == content_hash
    ).first()
    
    if existing_doc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A document with the same content already exists"
        )
    
    # Get user documents directory
    user_docs_dir = get_user_documents_dir(current_user.id)
    
    # Generate unique filename
    file_hash_short = content_hash[:16]
    safe_filename = "".join(c for c in file.filename if c.isalnum() or c in ".-_")[:200]
    unique_filename = f"{file_hash_short}_{safe_filename}"
    file_path = user_docs_dir / unique_filename
    
    # Save file
    with open(file_path, 'wb') as f:
        f.write(file_content)
    
    # Create database record
    document = UserDocument(
        user_id=current_user.id,
        filename=unique_filename,
        original_filename=file.filename,
        file_path=str(file_path),
        file_size=len(file_content),
        file_type=file_ext.lstrip('.'),
        content_hash=content_hash,
        is_indexed=0
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Index document asynchronously
    vector_store = get_vector_store()
    await vector_store.initialize()
    
    # Run indexing in background - pass document_id instead of document object
    # This ensures we create a fresh DB session in the background task
    document_id = document.id
    asyncio.create_task(
        index_user_document(document_id, file_path, vector_store)
    )
    
    # Ensure timezone-aware ISO format
    created_at_str = document.created_at.isoformat() if document.created_at else None
    if created_at_str and not created_at_str.endswith('Z') and '+' not in created_at_str:
        # If timezone info is missing, assume UTC and add Z
        created_at_str = created_at_str + 'Z'
    
    indexed_at_str = document.indexed_at.isoformat() if document.indexed_at else None
    if indexed_at_str and not indexed_at_str.endswith('Z') and '+' not in indexed_at_str:
        indexed_at_str = indexed_at_str + 'Z'
    
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        original_filename=document.original_filename,
        file_size=document.file_size,
        file_type=document.file_type,
        is_indexed=bool(document.is_indexed),
        indexed_at=indexed_at_str,
        created_at=created_at_str
    )


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all documents for the current user."""
    documents = db.query(UserDocument).filter(
        UserDocument.user_id == current_user.id
    ).order_by(UserDocument.created_at.desc()).all()
    
    result = []
    for doc in documents:
        # Ensure timezone-aware ISO format
        created_at_str = doc.created_at.isoformat() if doc.created_at else None
        if created_at_str and not created_at_str.endswith('Z') and '+' not in created_at_str:
            created_at_str = created_at_str + 'Z'
        
        indexed_at_str = doc.indexed_at.isoformat() if doc.indexed_at else None
        if indexed_at_str and not indexed_at_str.endswith('Z') and '+' not in indexed_at_str:
            indexed_at_str = indexed_at_str + 'Z'
        
        result.append(DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            original_filename=doc.original_filename,
            file_size=doc.file_size,
            file_type=doc.file_type,
            is_indexed=bool(doc.is_indexed),
            indexed_at=indexed_at_str,
            created_at=created_at_str
        ))
    
    return result


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a document."""
    document = db.query(UserDocument).filter(
        UserDocument.id == document_id,
        UserDocument.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Delete file
    file_path = Path(document.file_path)
    if file_path.exists():
        file_path.unlink()
    
    # Delete from vector store
    if document.is_indexed:
        try:
            vector_store = get_vector_store()
            collection_name = f"user_documents_{document.user_id}"
            
            # Get all chunks for this document
            # Note: This is a simplified approach. In production, you might want to
            # store chunk IDs in the database for more efficient deletion
            # For now, we'll clear the entire collection and re-index remaining documents
            # This is not ideal but works for MVP
            pass  # TODO: Implement proper chunk deletion
            
        except Exception as e:
            logger.error(f"Failed to delete document from vector store: {e}")
    
    # Delete database record
    db.delete(document)
    db.commit()
    
    return {"message": "Document deleted successfully"}


@router.post("/{document_id}/index")
async def reindex_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Re-index a document."""
    document = db.query(UserDocument).filter(
        UserDocument.id == document_id,
        UserDocument.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    file_path = Path(document.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found on disk"
        )
    
    # Index document
    vector_store = get_vector_store()
    await vector_store.initialize()
    
    success = await index_user_document(document.id, file_path, vector_store)
    
    if success:
        return {"message": "Document indexed successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to index document"
        )

