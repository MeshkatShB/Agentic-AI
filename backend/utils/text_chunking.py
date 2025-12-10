"""Text chunking utilities for document indexing."""

import hashlib
import re
from typing import List, Dict, Any


def enhanced_chunk_text(text: str, max_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
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

