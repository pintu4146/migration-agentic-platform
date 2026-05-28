"""
MCP Data Models

Pydantic models for MCP connector data structures.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class DocumentType(str, Enum):
    """Document type enumeration"""
    PAGE = "page"
    ATTACHMENT = "attachment"
    COMMENT = "comment"
    BLOG = "blog"
    DOCUMENT = "document"  # Added for uploaded documents
    UNKNOWN = "unknown"


class DocumentSource(str, Enum):
    """Document source enumeration"""
    CONTEXT_STUDIO = "context_studio"
    CONFLUENCE = "confluence"
    UPLOAD = "upload"
    QDRANT = "qdrant"  # For documents retrieved from Qdrant vector store
    UNKNOWN = "unknown"


class DocumentMetadata(BaseModel):
    """Document metadata"""
    
    source_id: Optional[str] = Field(default=None, description="Original source document ID")
    source_url: Optional[str] = Field(default=None, description="URL to source document")
    author: Optional[str] = Field(default=None, description="Document author")
    created_at: Optional[datetime] = Field(default=None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    version: Optional[str] = Field(default=None, description="Document version")
    space: Optional[str] = Field(default=None, description="Confluence space key")
    labels: List[str] = Field(default_factory=list, description="Document labels/tags")
    parent_id: Optional[str] = Field(default=None, description="Parent document ID")
    
    # Additional metadata
    word_count: Optional[int] = Field(default=None, description="Word count")
    page_count: Optional[int] = Field(default=None, description="Page count (for PDFs)")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    mime_type: Optional[str] = Field(default=None, description="MIME type")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "source_id": "page_123456",
            "source_url": "https://confluence.example.com/pages/123456",
            "author": "john.doe@example.com",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-15T00:00:00Z",
            "space": "PROJ",
            "labels": ["architecture", "migration"],
            "word_count": 1500
        }
    })


class Document(BaseModel):
    """Normalized document model"""
    
    id: str = Field(description="Unique document identifier")
    source: DocumentSource = Field(description="Document source")
    type: DocumentType = Field(description="Document type")
    title: str = Field(description="Document title")
    content: str = Field(description="Extracted text content")
    metadata: DocumentMetadata = Field(description="Document metadata")
    evidence_refs: List[str] = Field(
        default_factory=list,
        description="Evidence reference IDs for traceability"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for content extraction"
    )
    extracted_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Extraction timestamp"
    )
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "doc_abc123",
            "source": "context_studio",
            "type": "page",
            "title": "Architecture Overview",
            "content": "This document describes...",
            "metadata": {
                "source_id": "page_123456",
                "space": "PROJ"
            },
            "evidence_refs": ["ref_001", "ref_002"],
            "confidence": 0.95,
            "extracted_at": "2024-01-01T00:00:00Z"
        }
    })


class ContextPack(BaseModel):
    """Collection of retrieved documents"""
    
    project_id: str = Field(description="Project identifier")
    profile_name: str = Field(description="Retrieval profile used")
    documents: List[Document] = Field(description="Retrieved documents")
    total_count: int = Field(description="Total documents retrieved")
    retrieved_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Retrieval timestamp"
    )
    cache_key: Optional[str] = Field(
        default=None,
        description="Cache key for this context pack"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "project_id": "proj_abc123",
            "profile_name": "extraction_profile",
            "documents": [],
            "total_count": 5,
            "retrieved_at": "2024-01-01T00:00:00Z",
            "cache_key": "cache_xyz789",
            "metadata": {
                "query_time_ms": 1234,
                "cache_hit": False
            }
        }
    })


class MCPResponse(BaseModel):
    """Raw MCP Gateway response"""
    
    success: bool = Field(description="Request success status")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Response data")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "data": {"documents": []},
            "error": None,
            "metadata": {"request_id": "req_123"}
        }
    })


class MCPError(Exception):
    """Custom exception for MCP-related errors"""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(self.message)

# Made with Bob
