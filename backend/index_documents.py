#!/usr/bin/env python3
"""Script to index documents in the data directory."""

import asyncio
import os
import sys
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add the parent directory to Python path so we can import backend modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from backend.storage import get_vector_store
from backend.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def read_file_content(file_path: Path) -> str:
    """Read content from various file types with proper UTF-8 handling."""
    try:
        if file_path.suffix.lower() == '.html':
            from bs4 import BeautifulSoup
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            soup = BeautifulSoup(content, 'html.parser')
            # Get text and preserve Persian characters
            text = soup.get_text(separator=' ', strip=True)
            # Clean up extra whitespace while preserving Persian text
            import re
            text = re.sub(r'\s+', ' ', text)
            return text
        
        elif file_path.suffix.lower() == '.pdf':
            import pypdf
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        
        elif file_path.suffix.lower() == '.docx':
            import docx
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text.strip()
        
        elif file_path.suffix.lower() in ['.txt', '.md']:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().strip()
                # Clean up extra whitespace while preserving Persian text
                import re
                content = re.sub(r'\s+', ' ', content)
                return content
        
        else:
            # Try to read as text file
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().strip()
                # Clean up extra whitespace while preserving Persian text
                import re
                content = re.sub(r'\s+', ' ', content)
                return content
    
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return ""


async def index_documents():
    """Index all documents in the data directory."""
    data_dir = Path("data")
    
    if not data_dir.exists():
        logger.error("Data directory not found")
        return
    
    # Get vector store
    vector_store = get_vector_store()
    await vector_store.initialize()
    
    # Find all supported files
    supported_extensions = ['.html', '.pdf', '.docx', '.txt', '.md']
    files_to_index = []
    
    for file_path in data_dir.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            files_to_index.append(file_path)
    
    if not files_to_index:
        logger.info("No supported files found in data directory")
        return
    
    logger.info(f"Found {len(files_to_index)} files to index")
    
    # Process files in chunks with enhanced Persian-aware chunking
    chunk_size = settings.CHUNK_SIZE
    chunk_overlap = settings.CHUNK_OVERLAP
    documents = []
    metadatas = []
    
    def enhanced_chunk_text(text: str, max_size: int = chunk_size, overlap: int = chunk_overlap) -> List[Dict[str, Any]]:
        """Enhanced chunking that preserves Persian text integrity with overlap."""
        if len(text) <= max_size:
            return [{
                "text": text,
                "chunk_id": hashlib.md5(text.encode()).hexdigest()[:8],
                "start_pos": 0,
                "end_pos": len(text),
                "is_complete": True
            }]
        
        chunks = []
        
        # Split by paragraphs first
        paragraphs = re.split(r'\n\s*\n', text)
        
        for para_idx, paragraph in enumerate(paragraphs):
            if len(paragraph.strip()) == 0:
                continue
                
            if len(paragraph) <= max_size:
                chunks.append({
                    "text": paragraph.strip(),
                    "chunk_id": f"para_{para_idx}_{hashlib.md5(paragraph.encode()).hexdigest()[:8]}",
                    "start_pos": text.find(paragraph),
                    "end_pos": text.find(paragraph) + len(paragraph),
                    "is_complete": True
                })
            else:
                # Split long paragraphs by sentences
                sentences = re.split(r'[.!?؟۔]\s+', paragraph)
                current_chunk = ""
                chunk_start = text.find(paragraph)
                
                for sent_idx, sentence in enumerate(sentences):
                    if len(sentence.strip()) == 0:
                        continue
                        
                    if len(current_chunk) + len(sentence) <= max_size:
                        current_chunk += (" " + sentence if current_chunk else sentence)
                    else:
                        if current_chunk:
                            chunks.append({
                                "text": current_chunk.strip(),
                                "chunk_id": f"sent_{para_idx}_{sent_idx}_{hashlib.md5(current_chunk.encode()).hexdigest()[:8]}",
                                "start_pos": chunk_start,
                                "end_pos": chunk_start + len(current_chunk),
                                "is_complete": True
                            })
                        current_chunk = sentence
                        chunk_start = text.find(sentence)
                
                if current_chunk:
                    chunks.append({
                        "text": current_chunk.strip(),
                        "chunk_id": f"sent_{para_idx}_final_{hashlib.md5(current_chunk.encode()).hexdigest()[:8]}",
                        "start_pos": chunk_start,
                        "end_pos": chunk_start + len(current_chunk),
                        "is_complete": True
                    })
        
        # Add overlap between chunks for better context
        if overlap > 0 and len(chunks) > 1:
            enhanced_chunks = []
            for i, chunk in enumerate(chunks):
                enhanced_chunks.append(chunk)
                
                # Add overlap with next chunk if it exists
                if i < len(chunks) - 1:
                    next_chunk = chunks[i + 1]
                    overlap_text = chunk["text"][-overlap:] + " " + next_chunk["text"][:overlap]
                    if len(overlap_text.strip()) > 0:
                        enhanced_chunks.append({
                            "text": overlap_text.strip(),
                            "chunk_id": f"overlap_{i}_{hashlib.md5(overlap_text.encode()).hexdigest()[:8]}",
                            "start_pos": chunk["end_pos"] - overlap,
                            "end_pos": next_chunk["start_pos"] + overlap,
                            "is_complete": False,
                            "is_overlap": True
                        })
            
            return enhanced_chunks
        
        return [chunk for chunk in chunks if chunk["text"].strip()]
    
    for file_path in files_to_index:
        logger.info(f"Processing {file_path}")
        
        content = await read_file_content(file_path)
        if not content:
            continue
        
        # Use enhanced chunking for Persian text
        chunks = enhanced_chunk_text(content)
        total_chunks = len(chunks)
        
        for i, chunk in enumerate(chunks):
            documents.append(chunk["text"])
            metadatas.append({
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_type": file_path.suffix.lower().lstrip('.'),
                "chunk_index": i,
                "total_chunks": total_chunks,
                "chunk_id": chunk["chunk_id"],
                "start_pos": chunk["start_pos"],
                "end_pos": chunk["end_pos"],
                "is_complete": chunk["is_complete"],
                "is_overlap": chunk.get("is_overlap", False),
                "content_preview": chunk["text"][:100] + "..." if len(chunk["text"]) > 100 else chunk["text"],
                "word_count": len(chunk["text"].split()),
                "char_count": len(chunk["text"]),
                "indexed_at": datetime.utcnow().isoformat()
            })
    
    if documents:
        logger.info(f"Indexing {len(documents)} document chunks...")
        ids = await vector_store.add_documents(
            documents=documents,
            metadatas=metadatas,
            collection_name="documents"
        )
        logger.info(f"Successfully indexed {len(ids)} chunks")
    else:
        logger.info("No content to index")


if __name__ == "__main__":
    asyncio.run(index_documents())
