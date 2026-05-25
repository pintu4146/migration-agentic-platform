"""
MCP Connector

HTTP client for IBM Context Studio MCP Gateway with retry logic and error handling.
"""

import logging
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from ..config import settings
from ..tracing.langsmith import trace_operation
from .models import (
    MCPResponse,
    MCPError,
    ContextPack,
    Document,
    DocumentType,
    DocumentSource,
    DocumentMetadata
)
from .profiles import RetrievalProfile

logger = logging.getLogger(__name__)


class MCPConnector:
    """
    MCP Gateway connector with retry logic and caching.
    
    Handles communication with IBM Context Studio MCP Gateway.
    """
    
    def __init__(
        self,
        gateway_url: Optional[str] = None,
        gateway_token: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None
    ):
        """
        Initialize MCP connector.
        
        Args:
            gateway_url: MCP Gateway URL (defaults to settings)
            gateway_token: Bearer token (defaults to settings)
            api_key: Context Studio API key (defaults to settings)
            timeout: Request timeout in seconds (defaults to settings)
            max_retries: Maximum retry attempts (defaults to settings)
        """
        self.gateway_url = gateway_url or settings.mcp_gateway_url
        self.gateway_token = gateway_token or settings.mcp_gateway_token
        self.api_key = api_key or settings.mcp_api_key
        self.timeout = timeout or settings.mcp_timeout
        self.max_retries = max_retries or settings.mcp_max_retries
        
        # Validate configuration
        if not self.gateway_url:
            raise ValueError("MCP Gateway URL not configured")
        if not self.gateway_token:
            raise ValueError("MCP Gateway token not configured")
        if not self.api_key:
            raise ValueError("MCP API key not configured")
        
        # Create HTTP client
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers=self._get_headers(),
            follow_redirects=True
        )
        
        logger.info(f"MCP Connector initialized: {self.gateway_url}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for MCP requests"""
        return {
            "Authorization": f"Bearer {self.gateway_token}",
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Migration-Copilot/1.0"
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with retry logic.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            **kwargs: Additional request parameters
            
        Returns:
            HTTP response
            
        Raises:
            MCPError: On request failure
        """
        url = f"{self.gateway_url}/{endpoint.lstrip('/')}"
        
        try:
            logger.debug(f"MCP request: {method} {url}")
            response = await self.client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
            
        except httpx.HTTPStatusError as e:
            logger.error(f"MCP HTTP error: {e.response.status_code} - {e.response.text}")
            raise MCPError(
                message=f"MCP request failed: {e.response.status_code}",
                status_code=e.response.status_code,
                response_data=e.response.json() if e.response.text else None
            )
        except httpx.TimeoutException as e:
            logger.error(f"MCP timeout: {str(e)}")
            raise MCPError(message=f"MCP request timeout after {self.timeout}s")
        except httpx.NetworkError as e:
            logger.error(f"MCP network error: {str(e)}")
            raise MCPError(message=f"MCP network error: {str(e)}")
        except Exception as e:
            logger.error(f"MCP unexpected error: {str(e)}", exc_info=True)
            raise MCPError(message=f"Unexpected MCP error: {str(e)}")
    
    @trace_operation("mcp_retrieve", run_type="retriever", tags=["mcp", "retrieval"])
    async def retrieve(
        self,
        profile: RetrievalProfile,
        project_id: str,
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> ContextPack:
        """
        Retrieve documents using a retrieval profile.
        
        Args:
            profile: Retrieval profile configuration
            project_id: Project identifier
            additional_filters: Optional additional filters
            
        Returns:
            ContextPack with retrieved documents
            
        Raises:
            MCPError: On retrieval failure
        """
        logger.info(f"Retrieving context for project {project_id} with profile {profile.profile_name}")
        
        try:
            # Build query parameters
            query_params = self._build_query_params(profile, additional_filters)
            
            # Make request to MCP Gateway
            response = await self._make_request(
                method="POST",
                endpoint="/search",
                json=query_params
            )
            
            # Parse response
            response_data = response.json()
            
            # Normalize documents
            documents = self._normalize_documents(response_data, profile)
            
            # Create context pack
            context_pack = ContextPack(
                project_id=project_id,
                profile_name=profile.profile_name,
                documents=documents,
                total_count=len(documents),
                retrieved_at=datetime.utcnow(),
                cache_key=self._generate_cache_key(project_id, profile),
                metadata={
                    "query_params": query_params,
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "profile_type": profile.profile_type
                }
            )
            
            logger.info(f"Retrieved {len(documents)} documents for project {project_id}")
            return context_pack
            
        except MCPError:
            raise
        except Exception as e:
            logger.error(f"Failed to retrieve context: {str(e)}", exc_info=True)
            raise MCPError(message=f"Context retrieval failed: {str(e)}")
    
    def _build_query_params(
        self,
        profile: RetrievalProfile,
        additional_filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build query parameters from profile"""
        params: Dict[str, Any] = {
            "max_results": profile.max_results,
            "include_metadata": profile.include_metadata
        }
        
        # Source types
        if profile.source_types:
            params["source_types"] = profile.source_types
        
        # Content types
        if profile.content_types:
            params["content_types"] = profile.content_types
        
        # Page filters
        if profile.page_filters:
            params["page_filters"] = profile.page_filters
        
        # Attachment filters
        if profile.attachment_filters:
            params["attachment_filters"] = profile.attachment_filters
        
        # Keyword filters
        if profile.keyword_filters:
            params["keywords"] = profile.keyword_filters
        
        # Section filters
        if profile.section_filters:
            params["sections"] = profile.section_filters
        
        # Freshness
        if profile.freshness_days:
            cutoff_date = datetime.utcnow() - timedelta(days=profile.freshness_days)
            params["modified_after"] = cutoff_date.isoformat()
        
        # Include options
        params["include_attachments"] = profile.include_attachments
        params["include_comments"] = profile.include_comments
        
        # MCP-specific options
        if profile.mcp_options:
            params["mcp_options"] = profile.mcp_options
        
        # Additional filters
        if additional_filters:
            params.update(additional_filters)
        
        return params
    
    def _normalize_documents(
        self,
        response_data: Dict[str, Any],
        profile: RetrievalProfile
    ) -> List[Document]:
        """
        Normalize MCP response into Document objects.
        
        Args:
            response_data: Raw MCP response data
            profile: Retrieval profile used
            
        Returns:
            List of normalized Document objects
        """
        documents: List[Document] = []
        
        # Extract documents from response
        raw_documents = response_data.get("documents", [])
        
        for idx, raw_doc in enumerate(raw_documents):
            try:
                doc = self._normalize_single_document(raw_doc, idx)
                documents.append(doc)
            except Exception as e:
                logger.warning(f"Failed to normalize document {idx}: {str(e)}")
                continue
        
        return documents
    
    def _normalize_single_document(
        self,
        raw_doc: Dict[str, Any],
        index: int
    ) -> Document:
        """Normalize a single document"""
        
        # Extract basic fields
        doc_id = raw_doc.get("id", f"doc_{index}")
        title = raw_doc.get("title", "Untitled")
        content = raw_doc.get("content", raw_doc.get("body", ""))
        
        # Determine source and type
        source = self._determine_source(raw_doc)
        doc_type = self._determine_type(raw_doc)
        
        # Extract metadata
        metadata = self._extract_metadata(raw_doc)
        
        # Extract evidence references
        evidence_refs = raw_doc.get("evidence_refs", [])
        if not evidence_refs and "id" in raw_doc:
            evidence_refs = [raw_doc["id"]]
        
        # Calculate confidence
        confidence = self._calculate_confidence(raw_doc)
        
        return Document(
            id=doc_id,
            source=source,
            type=doc_type,
            title=title,
            content=content,
            metadata=metadata,
            evidence_refs=evidence_refs,
            confidence=confidence,
            extracted_at=datetime.utcnow()
        )
    
    def _determine_source(self, raw_doc: Dict[str, Any]) -> DocumentSource:
        """Determine document source"""
        source_str = raw_doc.get("source", "").lower()
        
        if "context" in source_str or "studio" in source_str:
            return DocumentSource.CONTEXT_STUDIO
        elif "confluence" in source_str:
            return DocumentSource.CONFLUENCE
        elif "upload" in source_str:
            return DocumentSource.UPLOAD
        else:
            return DocumentSource.UNKNOWN
    
    def _determine_type(self, raw_doc: Dict[str, Any]) -> DocumentType:
        """Determine document type"""
        doc_type = raw_doc.get("type", "").lower()
        
        if "page" in doc_type:
            return DocumentType.PAGE
        elif "attachment" in doc_type or "file" in doc_type:
            return DocumentType.ATTACHMENT
        elif "comment" in doc_type:
            return DocumentType.COMMENT
        elif "blog" in doc_type:
            return DocumentType.BLOG
        else:
            return DocumentType.UNKNOWN
    
    def _extract_metadata(self, raw_doc: Dict[str, Any]) -> DocumentMetadata:
        """Extract document metadata"""
        metadata_dict = raw_doc.get("metadata", {})
        
        return DocumentMetadata(
            source_id=raw_doc.get("id", ""),
            source_url=metadata_dict.get("url"),
            author=metadata_dict.get("author"),
            created_at=self._parse_datetime(metadata_dict.get("created_at")),
            updated_at=self._parse_datetime(metadata_dict.get("updated_at")),
            version=metadata_dict.get("version"),
            space=metadata_dict.get("space"),
            labels=metadata_dict.get("labels", []),
            parent_id=metadata_dict.get("parent_id"),
            word_count=len(raw_doc.get("content", "").split()),
            mime_type=metadata_dict.get("mime_type")
        )
    
    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string"""
        if not dt_str:
            return None
        
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except Exception:
            return None
    
    def _calculate_confidence(self, raw_doc: Dict[str, Any]) -> float:
        """Calculate confidence score for document"""
        confidence = 1.0
        
        # Reduce confidence if content is missing or short
        content = raw_doc.get("content", "")
        if not content:
            confidence *= 0.5
        elif len(content) < 100:
            confidence *= 0.7
        
        # Reduce confidence if metadata is incomplete
        metadata = raw_doc.get("metadata", {})
        if not metadata.get("author"):
            confidence *= 0.95
        if not metadata.get("updated_at"):
            confidence *= 0.95
        
        return max(0.0, min(1.0, confidence))
    
    def _generate_cache_key(
        self,
        project_id: str,
        profile: RetrievalProfile
    ) -> str:
        """Generate cache key for context pack"""
        # Create hash from project ID and profile
        key_data = f"{project_id}:{profile.profile_name}:{profile.model_dump_json()}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]
    
    async def health_check(self) -> bool:
        """
        Check MCP Gateway health.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self._make_request("GET", "/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"MCP health check failed: {str(e)}")
            return False
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
        logger.info("MCP Connector closed")
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

# Made with Bob
