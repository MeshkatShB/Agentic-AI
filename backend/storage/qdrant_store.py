"""Qdrant vector store implementation."""

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
    Record
)
from typing import List, Dict, Optional, Any
import uuid
from backend.config import settings
from .vector_store import VectorStore
import logging

logger = logging.getLogger(__name__)


class QdrantStore(VectorStore):
    """Qdrant implementation of vector store."""
    
    def __init__(self):
        """Initialize Qdrant client."""
        super().__init__()
        
        # Initialize Qdrant client
        self.client = QdrantClient(url=settings.QDRANT_URL)
        
        # Get embedding dimension
        test_embedding = self.generate_embedding("test")
        self.embedding_dim = len(test_embedding)
    
    async def initialize(self) -> bool:
        """Initialize the vector store."""
        try:
            # Create collections if they don't exist
            collections = ["conversations", "documents", "tools"]
            
            for collection_name in collections:
                if not self.client.collection_exists(collection_name):
                    self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=VectorParams(
                            size=self.embedding_dim,
                            distance=Distance.COSINE
                        )
                    )
                    logger.info(f"Created Qdrant collection: {collection_name}")
            
            logger.info("Qdrant initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")
            return False
    
    async def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict]] = None,
        ids: Optional[List[str]] = None,
        collection_name: str = "conversations"
    ) -> List[str]:
        """Add documents to the store."""
        
        # Generate IDs if not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
        
        # Generate embeddings
        embeddings = self.generate_embeddings(documents)
        
        # Ensure metadatas is provided
        if metadatas is None:
            metadatas = [{} for _ in documents]
        
        # Create points
        points = []
        for i, (doc_id, doc, embedding, metadata) in enumerate(zip(ids, documents, embeddings, metadatas)):
            # Add document to metadata
            metadata["document"] = doc
            
            point = PointStruct(
                id=doc_id,
                vector=embedding,
                payload=metadata
            )
            points.append(point)
        
        try:
            self.client.upsert(
                collection_name=collection_name,
                points=points
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
        
        # Generate query embedding
        query_embedding = self.generate_embedding(query)
        
        # Build filter if provided
        qdrant_filter = None
        if filter:
            conditions = []
            for key, value in filter.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
            
            if conditions:
                qdrant_filter = Filter(must=conditions)
        
        try:
            # Search
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=k,
                query_filter=qdrant_filter,
                with_payload=True,
                with_vectors=False
            )
            
            # Format results
            formatted_results = []
            for result in results:
                payload = result.payload or {}
                document = payload.pop("document", "")
                
                formatted_results.append({
                    "id": str(result.id),
                    "document": document,
                    "metadata": payload,
                    "score": result.score
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
        
        try:
            results = self.client.retrieve(
                collection_name=collection_name,
                ids=ids,
                with_payload=True,
                with_vectors=False
            )
            
            # Format results
            formatted_results = []
            for result in results:
                payload = result.payload or {}
                document = payload.pop("document", "")
                
                formatted_results.append({
                    "id": str(result.id),
                    "document": document,
                    "metadata": payload
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
        
        try:
            # Get existing document
            existing = await self.get_by_ids([id], collection_name)
            if not existing:
                logger.error(f"Document {id} not found")
                return False
            
            # Merge metadata
            updated_metadata = existing[0]["metadata"]
            if metadata:
                updated_metadata.update(metadata)
            
            # Update document in metadata
            if document:
                updated_metadata["document"] = document
                
                # Update with new embedding
                embedding = self.generate_embedding(document)
                
                point = PointStruct(
                    id=id,
                    vector=embedding,
                    payload=updated_metadata
                )
                
                self.client.upsert(
                    collection_name=collection_name,
                    points=[point]
                )
            else:
                # Just update metadata
                self.client.set_payload(
                    collection_name=collection_name,
                    payload=updated_metadata,
                    points=[id]
                )
            
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
        
        try:
            self.client.delete(
                collection_name=collection_name,
                points_selector=ids
            )
            
            logger.info(f"Deleted {len(ids)} documents from {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            return False
    
    async def clear_collection(self, collection_name: str) -> bool:
        """Clear all documents in a collection."""
        
        try:
            # Delete and recreate the collection
            self.client.delete_collection(collection_name=collection_name)
            
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )
            
            logger.info(f"Cleared collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear collection: {e}")
            return False
