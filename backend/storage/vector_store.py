"""Vector store abstraction."""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from sentence_transformers import SentenceTransformer
import numpy as np
import torch
from backend.config import settings


class VectorStore(ABC):
    """Abstract base class for vector storage."""
    
    def __init__(self):
        """Initialize the vector store.

        Note: We avoid eagerly loading the SentenceTransformer to prevent
        duplicated model memory usage in implementations that supply their own
        embedding function (e.g., Chroma with SentenceTransformerEmbeddingFunction).
        The embedding model will be created lazily on first use.
        """
        # Cache the device selection and defer model loading until needed
        self._device = self._get_device()
        self.embedding_model: Optional[SentenceTransformer] = None
    
    def _get_device(self) -> str:
        """Get the appropriate device for embeddings."""
        if settings.EMBEDDING_DEVICE == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"  # Apple Silicon GPU
            else:
                return "cpu"
        return settings.EMBEDDING_DEVICE
    
    def _get_embedding_model(self) -> SentenceTransformer:
        """Lazily create and return the embedding model instance."""
        if self.embedding_model is None:
            self.embedding_model = SentenceTransformer(
                settings.EMBEDDING_MODEL, device=self._device
            )
        return self.embedding_model

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        model = self._get_embedding_model()
        embedding = model.encode(text)
        return embedding.tolist()
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        model = self._get_embedding_model()
        embeddings = model.encode(texts)
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
        ids: Optional[List[str]] = None,
        collection_name: str = "conversations",
        embedding_model: Optional[str] = None
    ) -> List[str]:
        """Add documents to the store.
        
        Args:
            documents: List of document texts
            metadatas: Optional metadata for each document
            ids: Optional IDs for documents
            collection_name: Name of the collection
            embedding_model: Optional embedding model to use
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict] = None,
        collection_name: str = "conversations",
        embedding_model: Optional[str] = None
    ) -> List[Dict]:
        """Search for similar documents.
        
        Args:
            query: Search query text
            k: Number of results to return
            filter: Optional metadata filter
            collection_name: Name of the collection
            embedding_model: Optional embedding model to use
        """
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
