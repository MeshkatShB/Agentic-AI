"""ChromaDB vector store implementation."""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional, Any
import uuid
from backend.config import settings
from .vector_store import VectorStore
import logging

logger = logging.getLogger(__name__)


class ChromaStore(VectorStore):
    """ChromaDB implementation of vector store."""
    
    def __init__(self):
        """Initialize ChromaDB client."""
        super().__init__()
        
        # Initialize Chroma client with persistent storage
        self.client = chromadb.PersistentClient(
            path=settings.CHROMA_PATH,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        self.collections = {}
    
    async def initialize(self) -> bool:
        """Initialize the vector store."""
        try:
            # Create default collections
            self.collections["conversations"] = self.client.get_or_create_collection(
                name="conversations",
                metadata={"description": "Conversation history and messages"}
            )
            
            self.collections["documents"] = self.client.get_or_create_collection(
                name="documents",
                metadata={"description": "Indexed documents and files"}
            )
            
            self.collections["tools"] = self.client.get_or_create_collection(
                name="tools",
                metadata={"description": "Tool execution history"}
            )
            
            logger.info("ChromaDB initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            return False
    
    def _get_collection(self, collection_name: str = "conversations"):
        """Get or create a collection."""
        if collection_name not in self.collections:
            self.collections[collection_name] = self.client.get_or_create_collection(
                name=collection_name
            )
        return self.collections[collection_name]
    
    async def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None,
        collection_name: str = "conversations"
    ) -> List[str]:
        """Add documents to the store."""
        
        collection = self._get_collection(collection_name)
        
        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
        
        # Generate embeddings
        embeddings = self.generate_embeddings(documents)
        
        # Ensure metadatas is provided
        if metadatas is None:
            metadatas = [{} for _ in documents]
        
        try:
            collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(documents)} documents to {collection_name}")
            return ids
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            return []
    
    async def search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict] = None,
        collection_name: str = "conversations"
    ) -> List[Dict]:
        """Search for similar documents."""
        
        collection = self._get_collection(collection_name)
        
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        
        try:
            # Search with optional filter
            results = collection.query(
                query_embeddings=[query_embedding],
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
                update_args["embeddings"] = [self.generate_embedding(document)]
            
            if metadata:
                update_args["metadatas"] = [metadata]
            
            collection.update(**update_args)
            logger.info(f"Updated document {id} in {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update document: {e}")
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
            return False
    
    async def clear_collection(self, collection_name: str) -> bool:
        """Clear all documents in a collection."""
        
        try:
            # Delete and recreate the collection
            self.client.delete_collection(name=collection_name)
            self.collections[collection_name] = self.client.create_collection(
                name=collection_name
            )
            logger.info(f"Cleared collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False
