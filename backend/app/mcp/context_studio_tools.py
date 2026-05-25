"""
IBM Context Studio MCP Tools

Implements the specific MCP tools exposed by IBM Context Studio:
- context-broker-get-context-schema
- context-broker-vector-query
- context-broker-post-events
- context-broker-get-contexts
- context-broker-get-context-metadata
- context-broker-graph-query
- context-broker-hybrid-query
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ContextStudioTool(str, Enum):
    """Available Context Studio MCP tools"""
    GET_CONTEXT_SCHEMA = "context-broker-get-context-schema"
    VECTOR_QUERY = "context-broker-vector-query"
    POST_EVENTS = "context-broker-post-events"
    GET_CONTEXTS = "context-broker-get-contexts"
    GET_CONTEXT_METADATA = "context-broker-get-context-metadata"
    GRAPH_QUERY = "context-broker-graph-query"
    HYBRID_QUERY = "context-broker-hybrid-query"


class SchemaType(str, Enum):
    """Schema types for context-broker-get-context-schema"""
    METHOD = "method"
    ALL = "all"


class GetContextSchemaParams(BaseModel):
    """Parameters for context-broker-get-context-schema tool"""
    context_id: str = Field(description="Context ID (e.g., ctx_b4043773b9c6)")
    schema_name: Optional[str] = Field(
        default=None,
        description="Specific schema name to fetch, or None for all schemas"
    )
    type: Optional[SchemaType] = Field(
        default=None,
        description="Filter by type (e.g., 'method' for method schemas only)"
    )


class VectorQueryParams(BaseModel):
    """Parameters for context-broker-vector-query tool"""
    context_id: str = Field(description="Context ID")
    query: str = Field(description="Semantic search query")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum results to return")
    threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold (0.0-1.0)"
    )


class PostEventsParams(BaseModel):
    """Parameters for context-broker-post-events tool"""
    context_id: str = Field(description="Context ID")
    event_type: str = Field(description="Type of event (e.g., 'document_uploaded', 'artifact_generated')")
    source: str = Field(description="Source system (e.g., 'sharepoint', 'jira', 'github', 'splunk', 'sap')")
    payload: Dict[str, Any] = Field(description="Event payload with relevant data")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional metadata"
    )


class GetContextsParams(BaseModel):
    """Parameters for context-broker-get-contexts tool"""
    # No parameters needed - retrieves all contexts


class GetContextMetadataParams(BaseModel):
    """Parameters for context-broker-get-context-metadata tool"""
    context_id: str = Field(description="Context ID to retrieve metadata for")


class GraphQueryParams(BaseModel):
    """Parameters for context-broker-graph-query tool"""
    context_id: str = Field(description="Context ID")
    start_node: str = Field(description="Starting node ID for graph traversal")
    relationship_types: Optional[List[str]] = Field(
        default=None,
        description="Filter by relationship types"
    )
    max_depth: int = Field(
        default=1,
        ge=1,
        le=3,
        description="Maximum traversal depth (IMPORTANT: Use 1 to avoid timeouts)"
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum results (IMPORTANT: Use 5 to avoid timeouts)"
    )


class HybridQueryParams(BaseModel):
    """Parameters for context-broker-hybrid-query tool"""
    context_id: str = Field(description="Context ID")
    query: str = Field(description="Search query")
    vector_weight: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight for vector similarity (0.0-1.0)"
    )
    graph_weight: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight for graph relationships (0.0-1.0)"
    )
    max_depth: int = Field(default=1, ge=1, le=3, description="Graph traversal depth")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum results")


class ContextStudioToolCall(BaseModel):
    """MCP tool call request"""
    tool_name: ContextStudioTool
    parameters: Dict[str, Any]
    
    def to_mcp_request(self, request_id: int = 1) -> Dict[str, Any]:
        """Convert to MCP JSON-RPC tool call request"""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": self.tool_name.value,
                "arguments": self.parameters
            }
        }


class ContextStudioToolResponse(BaseModel):
    """MCP tool call response"""
    tool_name: str
    result: Any
    error: Optional[Dict[str, Any]] = None
    execution_time_ms: Optional[float] = None
    
    @classmethod
    def from_mcp_response(cls, response_data: Dict[str, Any], tool_name: str) -> "ContextStudioToolResponse":
        """Parse MCP JSON-RPC response"""
        if "error" in response_data:
            return cls(
                tool_name=tool_name,
                result=None,
                error=response_data["error"]
            )
        
        return cls(
            tool_name=tool_name,
            result=response_data.get("result"),
            error=None
        )


# Helper functions for common operations

def create_vector_query(
    context_id: str,
    query: str,
    limit: int = 10,
    threshold: Optional[float] = None
) -> ContextStudioToolCall:
    """Create a vector query tool call"""
    params = VectorQueryParams(
        context_id=context_id,
        query=query,
        limit=limit,
        threshold=threshold
    )
    
    return ContextStudioToolCall(
        tool_name=ContextStudioTool.VECTOR_QUERY,
        parameters=params.model_dump(exclude_none=True)
    )


def create_graph_query(
    context_id: str,
    start_node: str,
    relationship_types: Optional[List[str]] = None,
    max_depth: int = 1,
    limit: int = 5
) -> ContextStudioToolCall:
    """Create a graph query tool call (with safe defaults to avoid timeouts)"""
    params = GraphQueryParams(
        context_id=context_id,
        start_node=start_node,
        relationship_types=relationship_types,
        max_depth=max_depth,
        limit=limit
    )
    
    return ContextStudioToolCall(
        tool_name=ContextStudioTool.GRAPH_QUERY,
        parameters=params.model_dump(exclude_none=True)
    )


def create_hybrid_query(
    context_id: str,
    query: str,
    vector_weight: float = 0.5,
    graph_weight: float = 0.5,
    max_depth: int = 1,
    limit: int = 10
) -> ContextStudioToolCall:
    """Create a hybrid query tool call (combines vector + graph)"""
    params = HybridQueryParams(
        context_id=context_id,
        query=query,
        vector_weight=vector_weight,
        graph_weight=graph_weight,
        max_depth=max_depth,
        limit=limit
    )
    
    return ContextStudioToolCall(
        tool_name=ContextStudioTool.HYBRID_QUERY,
        parameters=params.model_dump(exclude_none=True)
    )


def create_post_event(
    context_id: str,
    event_type: str,
    source: str,
    payload: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> ContextStudioToolCall:
    """Create a post events tool call"""
    params = PostEventsParams(
        context_id=context_id,
        event_type=event_type,
        source=source,
        payload=payload,
        metadata=metadata
    )
    
    return ContextStudioToolCall(
        tool_name=ContextStudioTool.POST_EVENTS,
        parameters=params.model_dump(exclude_none=True)
    )


def create_get_context_metadata(context_id: str) -> ContextStudioToolCall:
    """Create a get context metadata tool call"""
    params = GetContextMetadataParams(context_id=context_id)
    
    return ContextStudioToolCall(
        tool_name=ContextStudioTool.GET_CONTEXT_METADATA,
        parameters=params.model_dump()
    )


def create_get_contexts() -> ContextStudioToolCall:
    """Create a get contexts tool call"""
    return ContextStudioToolCall(
        tool_name=ContextStudioTool.GET_CONTEXTS,
        parameters={}
    )


def create_get_context_schema(
    context_id: str,
    schema_name: Optional[str] = None,
    type: Optional[SchemaType] = None
) -> ContextStudioToolCall:
    """Create a get context schema tool call"""
    params = GetContextSchemaParams(
        context_id=context_id,
        schema_name=schema_name,
        type=type
    )
    
    return ContextStudioToolCall(
        tool_name=ContextStudioTool.GET_CONTEXT_SCHEMA,
        parameters=params.model_dump(exclude_none=True)
    )

# Made with Bob
