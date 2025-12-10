"""ChromaDB vector store implementation."""

import os
# Disable ChromaDB telemetry before importing
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_SERVER_NOFILE"] = "1"

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from typing import List, Dict, Optional, Any
from pathlib import Path
import json
import uuid
import torch
from backend.config import settings
from .vector_store import VectorStore
import logging

logger = logging.getLogger(__name__)

# Suppress ChromaDB telemetry logging
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)


class ChromaStore(VectorStore):
    """ChromaDB implementation of vector store."""
    
    def __init__(self, embedding_model: Optional[str] = None):
        """Initialize ChromaDB client.
        
        Args:
            embedding_model: Optional embedding model name. If None, uses default from settings.
        """
        super().__init__()
        
        # Store the embedding model name to use
        self.embedding_model_name = embedding_model or settings.EMBEDDING_MODEL
        
        # Cache for user-specific embedding functions (initialize before using)
        self._embedding_functions_cache: Dict[str, SentenceTransformerEmbeddingFunction] = {}
        
        # Get device for embedding function
        device = self._get_device()
        
        # Initialize default embedding function with configured model and device
        # This will be used for default collections, but user-specific collections
        # will use get_embedding_function() to get the appropriate model
        self.embedding_function = SentenceTransformerEmbeddingFunction(
            model_name=self.embedding_model_name,
            device=device
        )
        # Cache the default embedding function
        self._embedding_functions_cache[self.embedding_model_name] = self.embedding_function
        
        # Initialize Chroma client with persistent storage
        # Disable telemetry completely
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PATH,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True,
                chroma_client_auth_provider=None,
                chroma_client_auth_credentials=None
            )
        )
        
        self.collections = {}
    
    def get_embedding_function(self, embedding_model: Optional[str] = None) -> SentenceTransformerEmbeddingFunction:
        """Get or create an embedding function for a specific model.
        
        Args:
            embedding_model: Model name. If None, uses the default.
            
        Returns:
            SentenceTransformerEmbeddingFunction instance
        """
        model_name = embedding_model or self.embedding_model_name
        
        # Return cached if exists
        if model_name in self._embedding_functions_cache:
            return self._embedding_functions_cache[model_name]
        
        # Create new embedding function
        device = self._get_device()
        embedding_func = SentenceTransformerEmbeddingFunction(
            model_name=model_name,
            device=device
        )
        
        # Cache it
        self._embedding_functions_cache[model_name] = embedding_func
        return embedding_func
    
    async def initialize(self) -> bool:
        """Initialize the vector store."""
        try:
            # Ensure embedding compatibility across restarts (handle dim mismatch)
            self._ensure_embedding_compatibility()
            
            # Create default collections
            self.collections["conversations"] = self.client.get_or_create_collection(
                name="conversations",
                metadata={"description": "Conversation history and messages"},
                embedding_function=self.embedding_function
            )
            
            self.collections["documents"] = self.client.get_or_create_collection(
                name="documents",
                metadata={"description": "Indexed documents and files"},
                embedding_function=self.embedding_function
            )
            
            self.collections["tools"] = self.client.get_or_create_collection(
                name="tools",
                metadata={"description": "Tool execution history"},
                embedding_function=self.embedding_function
            )
            
            logger.info("ChromaDB initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            return False
    
    def _get_collection(self, collection_name: str = "conversations", embedding_model: Optional[str] = None):
        """Get or create a collection with optional embedding model.
        
        Args:
            collection_name: Name of the collection
            embedding_model: Optional embedding model name. If provided, uses that model.
        """
        # Use collection name + model as key to support different models per collection
        cache_key = f"{collection_name}_{embedding_model or self.embedding_model_name}"
        
        if cache_key not in self.collections:
            # Get the appropriate embedding function
            if embedding_model and embedding_model != self.embedding_model_name:
                embedding_func = self.get_embedding_function(embedding_model)
            else:
                embedding_func = self.embedding_function
            
            self.collections[cache_key] = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=embedding_func
            )
        return self.collections[cache_key]
    
    def get_collection(self, collection_name: str = "conversations"):
        """Get a collection by name."""
        return self._get_collection(collection_name)
    
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
        
        collection = self._get_collection(collection_name, embedding_model)
        
        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
        
        # Ensure metadatas is provided
        if metadatas is None:
            metadatas = [{} for _ in documents]
        
        try:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(documents)} documents to {collection_name}")
            return ids
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            if "dimension" in str(e).lower() or "dimensionality" in str(e).lower():
                # Auto-recover by recreating collection, then retry once
                await self.clear_collection(collection_name)
                try:
                    retry_collection = self._get_collection(collection_name)
                    retry_collection.add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    logger.info(f"Recovered and added {len(documents)} documents to {collection_name}")
                    return ids
                except Exception as e2:
                    logger.error(f"Retry after clearing collection failed: {e2}")
            return []
    
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
        
        collection = self._get_collection(collection_name, embedding_model)
        
        try:
            # Search with optional filter
            results = collection.query(
                query_texts=[query],
                n_results=k,
                where=filter if filter else None,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            if results["documents"] and len(results["documents"]) > 0:
                for i in range(len(results["documents"][0])):
                    formatted_results.append({
                        "id": results["ids"][0][i] if results["ids"] else None,
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "score": 1.0 - results["distances"][0][i] if results["distances"] else 0.0
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            if "dimension" in str(e).lower() or "dimensionality" in str(e).lower():
                await self.clear_collection(collection_name)
            return []
    
    async def get_by_ids(
        self,
        ids: List[str],
        collection_name: str = "conversations"
    ) -> List[Dict]:
        """Get documents by IDs."""
        
        collection = self._get_collection(collection_name)
        
        try:
            results = collection.get(
                ids=ids,
                include=["documents", "metadatas"]
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results["ids"])):
                formatted_results.append({
                    "id": results["ids"][i],
                    "document": results["documents"][i] if results["documents"] else None,
                    "metadata": results["metadatas"][i] if results["metadatas"] else {}
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to get documents by IDs: {e}")
            if "dimension" in str(e).lower() or "dimensionality" in str(e).lower():
                await self.clear_collection(collection_name)
            return []
    
    async def update_document(
        self,
        id: str,
        document: Optional[str] = None,
        metadata: Optional[Dict] = None,
        collection_name: str = "conversations"
    ) -> bool:
        """Update a document."""
        
        collection = self._get_collection(collection_name)
        
        try:
            update_args = {"ids": [id]}
            
            if document:
                update_args["documents"] = [document]
            
            if metadata:
                update_args["metadatas"] = [metadata]
            
            collection.update(**update_args)
            logger.info(f"Updated document {id} in {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update document: {e}")
            if "dimension" in str(e).lower() or "dimensionality" in str(e).lower():
                await self.clear_collection(collection_name)
            return False
    
    async def delete_documents(
        self,
        ids: List[str],
        collection_name: str = "conversations"
    ) -> bool:
        """Delete documents by IDs."""
        
        collection = self._get_collection(collection_name)
        
        try:
            collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents from {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            if "dimension" in str(e).lower() or "dimensionality" in str(e).lower():
                await self.clear_collection(collection_name)
            return False
    
    async def clear_collection(self, collection_name: str) -> bool:
        """Clear all documents in a collection."""
        
        try:
            # Delete and recreate the collection
            self.client.delete_collection(name=collection_name)
            self.collections[collection_name] = self.client.create_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            logger.info(f"Cleared collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False

    def _ensure_embedding_compatibility(self):
        """Ensure persisted collections match current embedding model; reset if changed."""
        try:
            meta_path = Path(settings.CHROMA_PATH) / "embedding_meta.json"
            current = {"model": settings.EMBEDDING_MODEL}
            if meta_path.exists():
                saved = json.loads(meta_path.read_text(encoding="utf-8"))
                if saved.get("model") != current["model"]:
                    # Model changed: drop known collections to avoid dimension mismatch
                    for name in ["documents", "conversations", "tools"]:
                        try:
                            self.client.delete_collection(name=name)
                        except Exception:
                            pass
                    meta_path.write_text(json.dumps(current), encoding="utf-8")
                # else: ok
            else:
                # First run: write meta
                Path(settings.CHROMA_PATH).mkdir(parents=True, exist_ok=True)
                meta_path.write_text(json.dumps(current), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not ensure embedding compatibility: {e}")
