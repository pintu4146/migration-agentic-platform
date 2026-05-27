"""
Qdrant Vector Store

Provides vector storage and semantic search using Qdrant.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
)

from app.config import settings

logger = logging.getLogger(__name__)


class QdrantStore:
    """
    Qdrant vector store for document embeddings.
    
    Provides:
    - Collection management
    - Document storage with embeddings
    - Semantic search
    - Metadata filtering
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None
    ):
        """
        Initialize Qdrant store.
        
        Args:
            host: Qdrant host (defaults to settings)
            port: Qdrant port (defaults to settings)
        """
        
        self.host = host or settings.qdrant_host
        self.port = port or settings.qdrant_port
        self.client: Optional[QdrantClient] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize Qdrant client and ensure connection."""
        
        if self._initialized:
            return
        
        try:
            # Create client
            self.client = QdrantClient(
                host=self.host,
                port=self.port,
                timeout=30
            )
            
            # Test connection
            collections = self.client.get_collections()
            logger.info(f"Connected to Qdrant at {self.host}:{self.port}")
            logger.info(f"Existing collections: {len(collections.collections)}")
            
            self._initialized = True
        
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {str(e)}")
            # For POC, use in-memory mode as fallback
            logger.warning("Using in-memory Qdrant mode")
            self.client = QdrantClient(":memory:")
            self._initialized = True
    
    async def create_collection(
        self,
        collection_name: str,
        vector_size: int = 768,
        distance: Distance = Distance.COSINE
    ):
        """
        Create a new collection.
        
        Args:
            collection_name: Name of collection
            vector_size: Dimension of vectors (768 for Gemini, 1536 for OpenAI)
            distance: Distance metric
        """
        
        if not self._initialized:
            await self.initialize()
        
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            existing = [c.name for c in collections.collections]
            
            if collection_name in existing:
                logger.info(f"Collection '{collection_name}' already exists")
                return
            
            # Create collection
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance
                )
            )
            
            logger.info(f"Created collection '{collection_name}' with vector size {vector_size}")
        
        except Exception as e:
            logger.error(f"Failed to create collection: {str(e)}")
            raise
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        collection_name: str
    ) -> int:
        """
        Add documents with embeddings to collection.
        
        Args:
            documents: List of document dicts with 'text', 'embedding', and 'metadata'
            collection_name: Target collection
            
        Returns:
            Number of documents added
        """
        
        if not self._initialized:
            await self.initialize()
        
        try:
            # Detect embedding dimension from first document
            first_embedding = documents[0].get('embedding')
            if not first_embedding:
                raise ValueError("First document missing embedding")
            
            vector_size = len(first_embedding)
            logger.info(f"Detected embedding dimension: {vector_size}")
            
            # Check if collection exists
            collections = self.client.get_collections()
            existing = [c.name for c in collections.collections]
            
            if collection_name in existing:
                # Collection exists - try to add documents
                # If dimensions don't match, Qdrant will error and we'll recreate
                logger.info(f"Collection '{collection_name}' exists, will attempt to add documents")
                try:
                    # Try a test upsert to check if dimensions match
                    test_point = PointStruct(
                        id="test_dimension_check",
                        vector=first_embedding,
                        payload={"test": True}
                    )
                    self.client.upsert(
                        collection_name=collection_name,
                        points=[test_point]
                    )
                    # Delete test point
                    self.client.delete(
                        collection_name=collection_name,
                        points_selector=["test_dimension_check"]
                    )
                    logger.info(f"Collection '{collection_name}' has correct dimensions")
                except Exception as dim_error:
                    if "dimension" in str(dim_error).lower():
                        logger.warning(f"Collection '{collection_name}' has wrong dimensions. Recreating...")
                        self.client.delete_collection(collection_name)
                        await self.create_collection(collection_name, vector_size=vector_size)
                    else:
                        raise
            else:
                # Create collection with detected dimensions
                await self.create_collection(collection_name, vector_size=vector_size)
            
            # Prepare points
            points = []
            
            for doc in documents:
                # Generate unique ID
                point_id = str(uuid.uuid4())
                
                # Extract embedding
                embedding = doc.get('embedding')
                if not embedding:
                    logger.warning(f"Document missing embedding, skipping")
                    continue
                
                # Prepare payload
                payload = {
                    'text': doc.get('text', ''),
                    'chunk_index': doc.get('chunk_index', 0),
                    'metadata': doc.get('metadata', {}),
                    'created_at': datetime.utcnow().isoformat()
                }
                
                # Create point
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
                
                points.append(point)
            
            if not points:
                logger.warning("No valid documents to add")
                return 0
            
            # Upload points
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            logger.info(f"Added {len(points)} documents to '{collection_name}'")
            return len(points)
        
        except Exception as e:
            logger.error(f"Failed to add documents: {str(e)}")
            raise
    
    async def search(
        self,
        query_embedding: List[float],
        collection_name: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        
        Args:
            query_embedding: Query vector
            collection_name: Collection to search
            limit: Maximum results
            filters: Metadata filters
            score_threshold: Minimum similarity score
            
        Returns:
            List of matching documents with scores
        """
        
        if not self._initialized:
            await self.initialize()
        
        try:
            # Build filter if provided
            query_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(
                        FieldCondition(
                            key=f"metadata.{key}",
                            match=MatchValue(value=value)
                        )
                    )
                
                if conditions:
                    query_filter = Filter(must=conditions)
            
            # Search
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit,
                query_filter=query_filter,
                score_threshold=score_threshold
            )
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'id': result.id,
                    'score': result.score,
                    'text': result.payload.get('text', ''),
                    'metadata': result.payload.get('metadata', {}),
                    'chunk_index': result.payload.get('chunk_index', 0)
                })
            
            logger.info(f"Found {len(formatted_results)} results in '{collection_name}'")
            return formatted_results
        
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise
    
    async def list_documents(
        self,
        collection_name: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List documents in collection.
        
        Args:
            collection_name: Collection name
            limit: Maximum documents to return
            
        Returns:
            List of document metadata
        """
        
        if not self._initialized:
            await self.initialize()
        
        try:
            # Scroll through collection
            records, _ = self.client.scroll(
                collection_name=collection_name,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )
            
            # Format documents
            documents = []
            for record in records:
                documents.append({
                    'id': record.id,
                    'text': record.payload.get('text', ''),
                    'metadata': record.payload.get('metadata', {}),
                    'chunk_index': record.payload.get('chunk_index', 0),
                    'created_at': record.payload.get('created_at')
                })
            
            logger.info(f"Listed {len(documents)} documents from '{collection_name}'")
            return documents
        
        except Exception as e:
            logger.error(f"Failed to list documents: {str(e)}")
            raise
    
    async def delete_document(
        self,
        document_id: str,
        collection_name: str
    ) -> int:
        """
        Delete a document by ID.
        
        Args:
            document_id: Document ID
            collection_name: Collection name
            
        Returns:
            Number of documents deleted
        """
        
        if not self._initialized:
            await self.initialize()
        
        try:
            # Delete by ID
            self.client.delete(
                collection_name=collection_name,
                points_selector=[document_id]
            )
            
            logger.info(f"Deleted document '{document_id}' from '{collection_name}'")
            return 1
        
        except Exception as e:
            logger.error(f"Failed to delete document: {str(e)}")
            raise
    
    async def delete_collection(self, collection_name: str):
        """
        Delete entire collection.
        
        Args:
            collection_name: Collection to delete
        """
        
        if not self._initialized:
            await self.initialize()
        
        try:
            self.client.delete_collection(collection_name=collection_name)
            logger.info(f"Deleted collection '{collection_name}'")
        
        except Exception as e:
            logger.error(f"Failed to delete collection: {str(e)}")
            raise
    
    async def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Get collection information.
        
        Args:
            collection_name: Collection name
            
        Returns:
            Collection info dictionary
        """
        
        if not self._initialized:
            await self.initialize()
        
        try:
            info = self.client.get_collection(collection_name=collection_name)
            
            return {
                'name': collection_name,
                'vectors_count': info.vectors_count,
                'points_count': info.points_count,
                'status': info.status,
                'config': {
                    'vector_size': info.config.params.vectors.size,
                    'distance': info.config.params.vectors.distance.name
                }
            }
        
        except Exception as e:
            logger.error(f"Failed to get collection info: {str(e)}")
            raise
    
    async def close(self):
        """Close Qdrant client connection."""
        
        if self.client:
            # Qdrant client doesn't need explicit closing
            self._initialized = False
            logger.info("Closed Qdrant connection")


# Made with Bob