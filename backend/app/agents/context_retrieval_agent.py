"""
Context Retrieval Agent

Responsibilities:
- Execute MCP retrieval using configured profile
- Fallback to uploaded documents if MCP fails
- Fallback to Qdrant cache if both fail
- Normalize context into unified format
- Preserve source IDs and evidence references
- Return state patch for orchestrator

Multi-Source Strategy:
1. Try MCP (IBM Context Studio) first
2. If MCP fails, try uploaded documents from Qdrant
3. If both fail, try cached context from previous runs
4. Return error only if all sources fail
"""

from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from ..mcp.connector import MCPConnector
from ..mcp.profiles import get_profile, ProfileType
from ..mcp.models import ContextPack, Document
from ..storage.qdrant_store import QdrantStore
from ..config import settings
from ..tracing.langsmith import trace_operation

logger = logging.getLogger(__name__)


class ContextRetrievalAgent:
    """
    Context Retrieval Agent - API-based, no LLM required.
    
    Fetches context from MCP (IBM Context Studio) and normalizes it
    for consumption by downstream agents.
    """
    
    def __init__(self):
        self.agent_name = "context_retrieval_agent"
    
    @trace_operation("context_retrieval_agent", run_type="chain", tags=["agent", "retrieval"])
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute context retrieval with multi-source fallback.
        
        Strategy:
        1. Try MCP (IBM Context Studio) first
        2. If MCP fails, try uploaded documents from Qdrant
        3. If both fail, try cached context
        4. Return error only if all sources fail
        
        Args:
            state: Current workflow state
            
        Returns:
            State patch with retrieved context
        """
        
        logger.info(f"[{self.agent_name}] Starting multi-source context retrieval")
        
        project_id = state.get("project_id")
        if not project_id:
            return self._error_response(state, "project_id is required in state")
        
        # Try each source in order
        sources_tried = []
        
        # Source 1: MCP (IBM Context Studio)
        context_pack, source = await self._try_mcp_retrieval(project_id, state)
        sources_tried.append(source)
        
        # Source 2: Uploaded Documents (if MCP failed)
        if context_pack is None:
            logger.warning(f"[{self.agent_name}] MCP retrieval failed, trying uploaded documents")
            context_pack, source = await self._try_uploaded_documents(project_id, state)
            sources_tried.append(source)
        
        # Source 3: Cached Context (if both failed)
        if context_pack is None:
            logger.warning(f"[{self.agent_name}] Uploaded documents failed, trying cache")
            context_pack, source = await self._try_cached_context(project_id, state)
            sources_tried.append(source)
        
        # All sources failed
        if context_pack is None:
            error_msg = f"All context sources failed: {', '.join(sources_tried)}"
            logger.error(f"[{self.agent_name}] {error_msg}")
            return self._error_response(state, error_msg)
        
        # Normalize context pack
        normalized_docs = self._normalize_context_pack(context_pack)
        
        logger.info(
            f"[{self.agent_name}] Retrieved {len(normalized_docs)} documents from {sources_tried[-1]}"
        )
        
        # Return state patch
        return {
            "context_pack": self._context_pack_to_dict(context_pack),
            "normalized_docs": normalized_docs,
            "phase": "extraction",
            "trace_metadata": {
                **state.get("trace_metadata", {}),
                "context_retrieval": {
                    "documents_retrieved": len(normalized_docs),
                    "source_used": sources_tried[-1],
                    "sources_tried": sources_tried,
                    "timestamp": datetime.utcnow().isoformat()
                }
            },
            "last_committed_by": self.agent_name,
            "last_committed_at": datetime.utcnow().isoformat()
        }
    
    async def _try_mcp_retrieval(
        self,
        project_id: str,
        state: Dict[str, Any]
    ) -> tuple[Optional[ContextPack], str]:
        """
        Try to retrieve context from MCP.
        
        Returns:
            (ContextPack or None, source_name)
        """
        
        try:
            # Get retrieval profile
            profile = get_profile(ProfileType.CONTEXT_RETRIEVAL)
            
            # Initialize MCP connector
            connector = MCPConnector(
                gateway_url=settings.mcp_gateway_url,
                gateway_token=settings.mcp_gateway_token,
                api_key=settings.mcp_api_key
            )
            
            # Execute retrieval
            logger.info(f"[{self.agent_name}] Trying MCP retrieval")
            context_pack = await connector.retrieve(
                profile=profile,
                project_id=project_id,
                query=state.get("mcp_request_profile", {}).get("query")
            )
            
            # Close connector
            await connector.close()
            
            if context_pack and context_pack.documents:
                logger.info(f"[{self.agent_name}] MCP retrieval successful: {len(context_pack.documents)} documents")
                return context_pack, "mcp"
            else:
                logger.warning(f"[{self.agent_name}] MCP returned no documents")
                return None, "mcp (no documents)"
        
        except Exception as e:
            logger.warning(f"[{self.agent_name}] MCP retrieval failed: {str(e)}")
            return None, f"mcp (error: {str(e)[:50]})"
    
    async def _try_uploaded_documents(
        self,
        project_id: str,
        state: Dict[str, Any]
    ) -> tuple[Optional[ContextPack], str]:
        """
        Try to retrieve uploaded documents from Qdrant.
        
        Returns:
            (ContextPack or None, source_name)
        """
        
        try:
            # Initialize Qdrant store
            qdrant_store = QdrantStore()
            await qdrant_store.initialize()
            
            # Get all documents for project
            logger.info(f"[{self.agent_name}] Trying uploaded documents from Qdrant")
            documents = await qdrant_store.list_documents(
                collection_name=f"project_{project_id}"
            )
            
            if not documents:
                logger.warning(f"[{self.agent_name}] No uploaded documents found")
                return None, "uploaded_documents (none found)"
            
            # Convert to ContextPack format
            context_pack = self._documents_to_context_pack(documents, project_id, "uploaded_documents")
            
            logger.info(f"[{self.agent_name}] Found {len(documents)} uploaded documents")
            return context_pack, "uploaded_documents"
        
        except Exception as e:
            logger.warning(f"[{self.agent_name}] Uploaded documents retrieval failed: {str(e)}")
            return None, f"uploaded_documents (error: {str(e)[:50]})"
    
    async def _try_cached_context(
        self,
        project_id: str,
        state: Dict[str, Any]
    ) -> tuple[Optional[ContextPack], str]:
        """
        Try to retrieve cached context from previous runs.
        
        Returns:
            (ContextPack or None, source_name)
        """
        
        try:
            # Check if state already has cached context
            cached_context = state.get("context_pack")
            
            if cached_context and cached_context.get("documents"):
                logger.info(f"[{self.agent_name}] Using cached context from state")
                # Reconstruct ContextPack from cached dict
                context_pack = self._dict_to_context_pack(cached_context)
                return context_pack, "cache"
            else:
                logger.warning(f"[{self.agent_name}] No cached context found")
                return None, "cache (none found)"
        
        except Exception as e:
            logger.warning(f"[{self.agent_name}] Cache retrieval failed: {str(e)}")
            return None, f"cache (error: {str(e)[:50]})"
    
    def _error_response(self, state: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
        """Create error response state patch."""
        return {
            "phase": "error",
            "last_error": error_msg,
            "error_log": [
                *state.get("error_log", []),
                {
                    "agent": self.agent_name,
                    "error": error_msg,
                    "timestamp": datetime.utcnow().isoformat()
                }
            ],
            "last_committed_by": self.agent_name,
            "last_committed_at": datetime.utcnow().isoformat()
        }
    
    def _context_pack_to_dict(self, context_pack: ContextPack) -> Dict[str, Any]:
        """
        Convert ContextPack Pydantic model to dict for state storage.
        
        Args:
            context_pack: ContextPack instance
            
        Returns:
            Dictionary representation
        """
        return {
            "project_id": context_pack.project_id,
            "profile_name": context_pack.profile_name,
            "total_count": context_pack.total_count,
            "retrieved_at": context_pack.retrieved_at.isoformat(),
            "cache_key": context_pack.cache_key,
            "metadata": context_pack.metadata,
            "documents": [self._document_to_dict(doc) for doc in context_pack.documents]
        }
    
    def _document_to_dict(self, doc: Document) -> Dict[str, Any]:
        """Convert Document model to dict"""
        return {
            "id": doc.id,
            "source": doc.source.value,
            "type": doc.type.value,
            "title": doc.title,
            "content": doc.content,
            "metadata": doc.metadata.model_dump() if doc.metadata else {},
            "evidence_refs": doc.evidence_refs,
            "confidence": doc.confidence,
            "extracted_at": doc.extracted_at.isoformat()
        }
    
    def _normalize_context_pack(self, context_pack: ContextPack) -> List[Dict[str, Any]]:
        """
        Normalize context pack into simplified document format for agents.
        
        Args:
            context_pack: ContextPack from MCP
            
        Returns:
            List of normalized documents
        """
        
        normalized_docs = []
        
        for idx, doc in enumerate(context_pack.documents):
            normalized_doc = {
                "doc_id": f"doc_{idx:03d}",
                "source_id": doc.id,
                "title": doc.title,
                "content": doc.content,
                "full_text": doc.content,
                "metadata": {
                    "source_type": doc.source.value,
                    "doc_type": doc.type.value,
                    "created_at": doc.metadata.created_at.isoformat() if doc.metadata and doc.metadata.created_at else None,
                    "updated_at": doc.metadata.updated_at.isoformat() if doc.metadata and doc.metadata.updated_at else None,
                    "author": doc.metadata.author if doc.metadata else None,
                    "source_url": doc.metadata.source_url if doc.metadata else None,
                    "word_count": doc.metadata.word_count if doc.metadata else len(doc.content.split()),
                },
                "evidence_refs": doc.evidence_refs,
                "confidence": doc.confidence,
                "chunks": self._chunk_document(doc.content, chunk_size=1000)
            }
            
            normalized_docs.append(normalized_doc)
        
        return normalized_docs
    
    def _chunk_document(self, content: str, chunk_size: int = 1000) -> List[str]:
        """
        Split document content into chunks for processing.
        
        Args:
            content: Document content
            chunk_size: Maximum chunk size in characters
            
        Returns:
            List of content chunks
        """
        
        if not content:
            return []
        
        chunks = []
        words = content.split()
        current_chunk = []
        current_length = 0
        
        for word in words:
            word_length = len(word) + 1  # +1 for space
            
            if current_length + word_length > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = [word]
                current_length = word_length
            else:
                current_chunk.append(word)
                current_length += word_length
        
        if current_chunk:
            chunks.append(" ".join(current_chunk))
        
        return chunks


# Made with Bob
    def _documents_to_context_pack(
        self,
        documents: List[Dict[str, Any]],
        project_id: str,
        source_name: str
    ) -> ContextPack:
        """
        Convert Qdrant documents to ContextPack format.
        
        Args:
            documents: List of document dicts from Qdrant
            project_id: Project ID
            source_name: Source name for metadata
            
        Returns:
            ContextPack instance
        """
        
        from ..mcp.models import DocumentSource, DocumentType, DocumentMetadata
        
        doc_objects = []
        
        for doc in documents:
            # Extract metadata
            metadata = doc.get('metadata', {})
            
            # Create Document object
            doc_obj = Document(
                id=doc.get('id', f"doc_{len(doc_objects)}"),
                source=DocumentSource.UPLOAD,
                type=DocumentType.DOCUMENT,
                title=metadata.get('source_file', 'Uploaded Document'),
                content=doc.get('text', ''),
                metadata=DocumentMetadata(
                    author=metadata.get('author'),
                    created_at=metadata.get('created_date'),
                    source_url=None,
                    word_count=len(doc.get('text', '').split())
                ),
                evidence_refs=[],
                confidence=1.0,
                extracted_at=datetime.utcnow()
            )
            
            doc_objects.append(doc_obj)
        
        # Create ContextPack
        return ContextPack(
            project_id=project_id,
            profile_name=source_name,
            documents=doc_objects,
            total_count=len(doc_objects),
            retrieved_at=datetime.utcnow(),
            cache_key=f"{project_id}_{source_name}_{datetime.utcnow().timestamp()}",
            metadata={"source": source_name}
        )
    
    def _dict_to_context_pack(self, context_dict: Dict[str, Any]) -> ContextPack:
        """
        Reconstruct ContextPack from dictionary.
        
        Args:
            context_dict: Dictionary representation of ContextPack
            
        Returns:
            ContextPack instance
        """
        
        from ..mcp.models import DocumentSource, DocumentType, DocumentMetadata
        
        doc_objects = []
        
        for doc_dict in context_dict.get('documents', []):
            # Reconstruct metadata
            meta_dict = doc_dict.get('metadata', {})
            metadata = DocumentMetadata(
                author=meta_dict.get('author'),
                created_at=meta_dict.get('created_at'),
                updated_at=meta_dict.get('updated_at'),
                source_url=meta_dict.get('source_url'),
                word_count=meta_dict.get('word_count')
            )
            
            # Reconstruct Document
            doc_obj = Document(
                id=doc_dict['id'],
                source=DocumentSource(doc_dict['source']),
                type=DocumentType(doc_dict['type']),
                title=doc_dict['title'],
                content=doc_dict['content'],
                metadata=metadata,
                evidence_refs=doc_dict.get('evidence_refs', []),
                confidence=doc_dict.get('confidence', 1.0),
                extracted_at=datetime.fromisoformat(doc_dict['extracted_at'])
            )
            
            doc_objects.append(doc_obj)
        
        # Reconstruct ContextPack
        return ContextPack(
            project_id=context_dict['project_id'],
            profile_name=context_dict['profile_name'],
            documents=doc_objects,
            total_count=context_dict['total_count'],
            retrieved_at=datetime.fromisoformat(context_dict['retrieved_at']),
            cache_key=context_dict.get('cache_key', ''),
            metadata=context_dict.get('metadata', {})
        )
