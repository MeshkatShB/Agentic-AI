"""Vector store abstraction."""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from sentence_transformers import SentenceTransformer
import numpy as np
from backend.config import settings


class VectorStore(ABC):
    """Abstract base class for vector storage."""
    
    def __init__(self):
        """Initialize the vector store."""
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        embedding = self.embedding_model.encode(text)
        return embedding.tolist()
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = self.embedding_model.encode(texts)
        return embeddings.tolist()
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the vector store."""
        pass
    
    @abstractmethod
    async def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """Add documents to the store."""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict] = None
    ) -> List[Dict]:
        """Search for similar documents."""
        pass
    
    @abstractmethod
    async def get_by_ids(self, ids: List[str]) -> List[Dict]:
        """Get documents by IDs."""
        pass
    
    @abstractmethod
    async def update_document(
        self,
        id: str,
        document: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Update a document."""
        pass
    
    @abstractmethod
    async def delete_documents(self, ids: List[str]) -> bool:
        """Delete documents by IDs."""
        pass
    
    @abstractmethod
    async def clear_collection(self, collection_name: str) -> bool:
        """Clear all documents in a collection."""
        pass


def get_vector_store() -> VectorStore:
    """Factory function to get the configured vector store."""
    
    store_type = settings.VECTOR_STORE.lower()
    
    if store_type == "chroma":
        from .chroma_store import ChromaStore
        return ChromaStore()
    elif store_type == "qdrant":
        from .qdrant_store import QdrantStore
        return QdrantStore()
    else:
        raise ValueError(f"Unknown vector store type: {store_type}")
