"""
Qdrant Client

Vector store client for context retrieval fallback.
Follows Single Responsibility Principle - only Qdrant operations.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from qdrant_client import QdrantClient as QdrantSDK
from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
    Distance,
    VectorParams,
    PointStruct
)

from ..config import settings
from ..mcp.models import ContextPack, Document, DocumentSource, DocumentType, DocumentMetadata
from .qdrant_profiles import QdrantSearchProfile

logger = logging.getLogger(__name__)


class QdrantClient:
    """
    Async Qdrant client for vector search.
    
    Responsibilities:
    - Search documents by semantic similarity
    - Filter by metadata
    - Return ContextPack (same format as MCP)
    
    Design Principles:
    - KISS: Simple search operations
    - DRY: Reusable filter building
    - SOLID: Single responsibility (Qdrant only)
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None
    ):
        """Initialize Qdrant client."""
        self.host = host or settings.qdrant_host
        self.port = port or settings.qdrant_port
        self.client = QdrantSDK(host=self.host, port=self.port)
        logger.info(f"Initialized Qdrant client: {self.host}:{self.port}")
    
    async def search(
        self,
        profile: QdrantSearchProfile,
        query: str,
        project_id: str
    ) -> ContextPack:
        """
        Search Qdrant using profile configuration.
        
        Args:
            profile: Search profile
            query: Search query text
            project_id: Project identifier
            
        Returns:
            ContextPack with search results
        """
        try:
            # Format collection name with project_id
            collection_name = profile.collection_name.format(project_id=project_id)
            
            # Build filters
            filters = self._build_filters(profile, project_id)
            
            # POC: Use scroll to get all documents instead of semantic search
            # This avoids the embedding API dependency for now
            logger.info(f"Retrieving documents from collection: {collection_name}")
            logger.info(f"Filter being applied: {filters}")
            
            # First, try without filter to see if documents exist
            all_results, _ = self.client.scroll(
                collection_name=collection_name,
                limit=profile.limit,
                with_payload=True,
                with_vectors=False
            )
            logger.info(f"Total documents in collection (no filter): {len(all_results)}")
            
            if all_results:
                # Log first document structure
                logger.info(f"Sample document payload keys: {list(all_results[0].payload.keys())}")
                logger.info(f"Sample document payload: {all_results[0].payload}")
            
            # Now try with filter
            results, _ = self.client.scroll(
                collection_name=collection_name,
                scroll_filter=filters,
                limit=profile.limit,
                with_payload=profile.with_payload,
                with_vectors=False
            )
            
            logger.info(f"Documents after filter: {len(results)}")
            
            # Convert to Document objects
            documents = [
                self._convert_to_document(hit)
                for hit in results
            ]
            
            logger.info(
                f"Qdrant search: {len(documents)} docs "
                f"(profile={profile.profile_name}, query='{query[:50]}...')"
            )
            
            # Return ContextPack (same format as MCP)
            return ContextPack(
                project_id=project_id,
                profile_name=profile.profile_name,
                documents=documents,
                total_count=len(documents),
                retrieved_at=datetime.utcnow(),
                metadata={
                    "source": "qdrant",
                    "collection": profile.collection_name,
                    "score_threshold": profile.score_threshold,
                    "query": query
                }
            )
            
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}", exc_info=True)
            # Return empty ContextPack on error
            return ContextPack(
                project_id=project_id,
                profile_name=profile.profile_name,
                documents=[],
                total_count=0,
                retrieved_at=datetime.utcnow(),
                metadata={"source": "qdrant", "error": str(e)}
            )
    
    def _build_filters(
        self,
        profile: QdrantSearchProfile,
        project_id: str
    ) -> Optional[Filter]:
        """
        Build Qdrant filters from profile.
        
        Args:
            profile: Search profile
            project_id: Project identifier
            
        Returns:
            Qdrant Filter or None
        """
        conditions = []
        
        # Add project filter - project_id is stored in metadata
        conditions.append(
            FieldCondition(
                key="metadata.project_id",
                match=MatchValue(value=project_id)
            )
        )
        
        # Add metadata filters from profile
        if profile.metadata_filters:
            for key, value in profile.metadata_filters.items():
                if isinstance(value, list):
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchAny(any=value)
                        )
                    )
                else:
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
        
        # Add content type filter
        if profile.content_type_filter:
            conditions.append(
                FieldCondition(
                    key="content_type",
                    match=MatchAny(any=profile.content_type_filter)
                )
            )
        
        return Filter(must=conditions) if conditions else None
    
    def _convert_to_document(self, hit: Any) -> Document:
        """
        Convert Qdrant search hit to Document.
        
        Args:
            hit: Qdrant search result
            
        Returns:
            Document object
        """
        payload = hit.payload
        
        return Document(
            id=payload.get("id", str(hit.id)),
            source=DocumentSource.QDRANT,
            type=DocumentType(payload.get("type", "page")),
            title=payload.get("title", "Untitled"),
            content=payload.get("content", ""),
            metadata=DocumentMetadata(
                source_id=payload.get("source_id"),
                source_url=payload.get("source_url"),
                author=payload.get("author"),
                created_at=self._parse_datetime(payload.get("created_at")),
                updated_at=self._parse_datetime(payload.get("updated_at")),
                version=payload.get("version"),
                space=payload.get("space"),
                labels=payload.get("labels", []),
                parent_id=payload.get("parent_id"),
                word_count=payload.get("word_count", 0),
                mime_type=payload.get("mime_type")
            ),
            evidence_refs=payload.get("evidence_refs", []),
            confidence=getattr(hit, 'score', 1.0),  # Use score if available (search), else 1.0 (scroll)
            extracted_at=datetime.utcnow()
        )
    
    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string safely."""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except Exception:
            return None
    
    async def _get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        
        TODO: Integrate with OpenAI/Gemini embedding API
        For now, returns dummy embedding.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector
        """
        # Placeholder - will integrate with LLM provider in Phase 4
        # For now, return zero vector of correct dimension
        # Match the dimension used during document upload (3072 for text-embedding-3-large)
        return [0.0] * 3072  # OpenAI text-embedding-3-large dimension
    
    async def create_collection(
        self,
        collection_name: str,
        vector_size: int = 1536,
        distance: Distance = Distance.COSINE
    ) -> bool:
        """
        Create Qdrant collection.
        
        Args:
            collection_name: Collection name
            vector_size: Vector dimension
            distance: Distance metric
            
        Returns:
            True if created successfully
        """
        try:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance
                )
            )
            logger.info(f"Created Qdrant collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create collection: {e}")
            return False
    
    async def upsert_documents(
        self,
        collection_name: str,
        documents: List[Document],
        project_id: str
    ) -> bool:
        """
        Upsert documents to Qdrant.
        
        Args:
            collection_name: Collection name
            documents: Documents to upsert
            project_id: Project identifier
            
        Returns:
            True if successful
        """
        try:
            points = []
            for doc in documents:
                # Generate embedding for document content
                embedding = await self._get_embedding(doc.content)
                
                # Create point
                point = PointStruct(
                    id=doc.id,
                    vector=embedding,
                    payload={
                        "id": doc.id,
                        "project_id": project_id,
                        "source": doc.source.value,
                        "type": doc.type.value,
                        "title": doc.title,
                        "content": doc.content,
                        "source_id": doc.metadata.source_id,
                        "source_url": doc.metadata.source_url,
                        "author": doc.metadata.author,
                        "created_at": doc.metadata.created_at.isoformat() if doc.metadata.created_at else None,
                        "updated_at": doc.metadata.updated_at.isoformat() if doc.metadata.updated_at else None,
                        "version": doc.metadata.version,
                        "space": doc.metadata.space,
                        "labels": doc.metadata.labels,
                        "parent_id": doc.metadata.parent_id,
                        "word_count": doc.metadata.word_count,
                        "mime_type": doc.metadata.mime_type,
                        "evidence_refs": doc.evidence_refs,
                    }
                )
                points.append(point)
            
            # Upsert to Qdrant
            self.client.upsert(
                collection_name=collection_name,
                points=points
            )
            
            logger.info(f"Upserted {len(points)} documents to Qdrant")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert documents: {e}")
            return False


# Singleton instance
_qdrant_client: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    """
    Get or create Qdrant client singleton.
    
    Returns:
        QdrantClient instance
    """
    global _qdrant_client
    
    if _qdrant_client is None:
        _qdrant_client = QdrantClient()
    
    return _qdrant_client

# Made with Bob
