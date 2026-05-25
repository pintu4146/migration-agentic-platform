"""
Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class ProviderType(str, Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    GEMINI = "gemini"


class ProviderHealthStatus(str, Enum):
    """Provider health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class PhaseType(str, Enum):
    """Workflow phases"""
    INIT = "init"
    CONTEXT_RETRIEVAL = "context_retrieval"
    EXTRACTION = "extraction"
    QUESTIONNAIRE = "questionnaire"
    INTAKE_DRAFT = "intake_draft"
    REVIEW = "review"
    MIGRATION_PLANNING = "migration_planning"
    COMPLETE = "complete"
    ERROR = "error"


# ============================================================================
# Health Check Schemas
# ============================================================================

class HealthResponse(BaseModel):
    """API health check response"""
    status: str = Field(default="healthy", description="Service health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(default="1.0.0", description="API version")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",
            "version": "1.0.0"
        }
    })


class ProviderStatus(BaseModel):
    """Individual provider status"""
    provider: ProviderType
    status: ProviderHealthStatus
    model: Optional[str] = None
    last_check: Optional[datetime] = None
    error: Optional[str] = None
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "provider": "openai",
            "status": "healthy",
            "model": "gpt-4",
            "last_check": "2024-01-01T00:00:00Z"
        }
    })


class ProviderHealthResponse(BaseModel):
    """Provider health check response"""
    primary: ProviderStatus
    fallback: Optional[ProviderStatus] = None
    active_provider: ProviderType
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "primary": {
                "provider": "openai",
                "status": "healthy",
                "model": "gpt-4"
            },
            "fallback": {
                "provider": "gemini",
                "status": "healthy",
                "model": "gemini-pro"
            },
            "active_provider": "openai"
        }
    })


# ============================================================================
# Error Schemas
# ============================================================================

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "error": "Validation error",
            "detail": "Invalid project ID format",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    })


# ============================================================================
# Project Schemas
# ============================================================================

class ProjectCreateRequest(BaseModel):
    """Request to create a new migration project"""
    name: str = Field(min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(default=None, description="Project description")
    mcp_config: Optional[Dict[str, Any]] = Field(
        default=None,
        description="MCP connector configuration"
    )
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "name": "Legacy App Migration",
            "description": "Migrate legacy monolith to microservices",
            "mcp_config": {
                "base_url": "https://confluence.example.com",
                "space_key": "PROJ",
                "page_ids": ["123456"]
            }
        }
    })


class ProjectResponse(BaseModel):
    """Project information response"""
    project_id: str = Field(description="Unique project identifier")
    name: str
    description: Optional[str] = None
    phase: PhaseType = Field(default=PhaseType.INIT)
    state_version: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "project_id": "proj_abc123",
            "name": "Legacy App Migration",
            "description": "Migrate legacy monolith to microservices",
            "phase": "init",
            "state_version": 0,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }
    })


# ============================================================================
# State Schemas
# ============================================================================

class StateResponse(BaseModel):
    """Workflow state response"""
    project_id: str
    state_version: int
    phase: PhaseType
    context_pack: Optional[Dict[str, Any]] = None
    extracted_facts: Optional[Dict[str, Any]] = None
    missing_questions: Optional[List[Dict[str, Any]]] = None
    intake_draft: Optional[Dict[str, Any]] = None
    migration_plan: Optional[Dict[str, Any]] = None
    human_reviewed: bool = Field(default=False)
    last_committed_by: Optional[str] = None
    last_committed_at: Optional[datetime] = None
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "project_id": "proj_abc123",
            "state_version": 5,
            "phase": "extraction",
            "context_pack": {"documents": []},
            "extracted_facts": None,
            "human_reviewed": False,
            "last_committed_by": "context_retrieval_agent",
            "last_committed_at": "2024-01-01T00:00:00Z"
        }
    })


# ============================================================================
# MCP Schemas
# ============================================================================

class MCPRetrievalProfile(BaseModel):
    """MCP retrieval profile configuration"""
    profile_name: str = Field(description="Profile identifier")
    source_types: Optional[List[str]] = Field(
        default=None,
        description="Source types to retrieve (page, attachment, etc.)"
    )
    content_types: Optional[List[str]] = Field(
        default=None,
        description="Content types to filter"
    )
    page_filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Page-specific filters"
    )
    max_results: int = Field(default=100, ge=1, le=1000)
    freshness_days: Optional[int] = Field(
        default=None,
        ge=1,
        description="Only retrieve content modified within N days"
    )
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "profile_name": "extraction_profile",
            "source_types": ["page", "attachment"],
            "content_types": ["application/pdf", "text/plain"],
            "page_filters": {"space": "PROJ"},
            "max_results": 50,
            "freshness_days": 90
        }
    })


class MCPRetrievalRequest(BaseModel):
    """Request to retrieve context from MCP"""
    project_id: str
    profile: MCPRetrievalProfile
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "project_id": "proj_abc123",
            "profile": {
                "profile_name": "extraction_profile",
                "source_types": ["page"],
                "max_results": 50
            }
        }
    })


class MCPRetrievalResponse(BaseModel):
    """Response from MCP retrieval"""
    project_id: str
    profile_name: str
    documents: List[Dict[str, Any]] = Field(description="Retrieved documents")
    total_count: int = Field(description="Total documents retrieved")
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "project_id": "proj_abc123",
            "profile_name": "extraction_profile",
            "documents": [
                {
                    "id": "page_123",
                    "title": "Architecture Overview",
                    "content": "...",
                    "source": "confluence"
                }
            ],
            "total_count": 1,
            "retrieved_at": "2024-01-01T00:00:00Z"
        }
    })


# ============================================================================
# Agent Execution Schemas
# ============================================================================

class AgentExecutionRequest(BaseModel):
    """Request to execute an agent"""
    project_id: str
    agent_name: str
    input_data: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "project_id": "proj_abc123",
            "agent_name": "extraction_agent",
            "input_data": {"force_refresh": False}
        }
    })


class AgentExecutionResponse(BaseModel):
    """Response from agent execution"""
    project_id: str
    agent_name: str
    success: bool
    output_patch: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: float
    trace_url: Optional[str] = None
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "project_id": "proj_abc123",
            "agent_name": "extraction_agent",
            "success": True,
            "output_patch": {"extracted_facts": {}},
            "execution_time_ms": 1234.56,
            "trace_url": "https://smith.langchain.com/..."
        }
    })


# ============================================================================
# MCP Health Check Schema
# ============================================================================

class MCPHealthResponse(BaseModel):
    """MCP Gateway health check response"""
    gateway_url: str
    status: str
    last_check: Optional[datetime] = None
    error: Optional[str] = None
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "gateway_url": "https://servicesessentials.ibm.com/mcp-gateway/...",
            "status": "healthy",
            "last_check": "2024-01-01T00:00:00Z",
            "error": None
        }
    })

# Made with Bob
