# Phase 2: IBM Context Studio MCP Tools Integration

## Overview

This document describes the integration of IBM Context Studio specific MCP tools into the migration copilot. The Context Studio provides 7 specialized tools for intelligent context retrieval and management.

## Available Context Studio MCP Tools

### 1. context-broker-get-context-schema
**Purpose:** Retrieves ontology schema in JSON-LD format for a given context

**Use Case:** Understanding the structure and relationships in the knowledge base

**Parameters:**
- `context_id` (required): Context ID (e.g., `ctx_b4043773b9c6`)
- `schema_name` (optional): Specific schema name to fetch
- `type` (optional): Filter by type (e.g., `method` for method schemas only)

**Example:**
```python
from backend.app.mcp.context_studio_tools import create_get_context_schema

tool_call = create_get_context_schema(
    context_id="ctx_b4043773b9c6",
    schema_name=None,  # Get all schemas
    type="method"  # Only method schemas
)
```

### 2. context-broker-vector-query
**Purpose:** Performs vector-based semantic search over indexed knowledge using embeddings

**Use Case:** Finding semantically similar content for migration analysis

**Parameters:**
- `context_id` (required): Context ID
- `query` (required): Semantic search query
- `limit` (optional, default=10): Maximum results to return (1-100)
- `threshold` (optional): Minimum similarity threshold (0.0-1.0)

**Example:**
```python
from backend.app.mcp.context_studio_tools import create_vector_query

tool_call = create_vector_query(
    context_id="ctx_b4043773b9c6",
    query="microservices architecture patterns",
    limit=20,
    threshold=0.7
)
```

### 3. context-broker-post-events
**Purpose:** Dispatches structured event notifications to trigger data processing or synchronization

**Use Case:** Notifying Context Studio when new artifacts are generated or reviewed

**Parameters:**
- `context_id` (required): Context ID
- `event_type` (required): Type of event (e.g., `document_uploaded`, `artifact_generated`)
- `source` (required): Source system (e.g., `sharepoint`, `jira`, `github`, `splunk`, `sap`)
- `payload` (required): Event payload with relevant data
- `metadata` (optional): Additional metadata

**Example:**
```python
from backend.app.mcp.context_studio_tools import create_post_event

tool_call = create_post_event(
    context_id="ctx_b4043773b9c6",
    event_type="migration_plan_generated",
    source="migration-copilot",
    payload={
        "project_id": "proj_abc123",
        "plan_version": "1.0",
        "file_url": "https://sharepoint.com/plans/migration-plan-v1.pdf"
    },
    metadata={
        "generated_by": "migration_planning_agent",
        "timestamp": "2026-05-25T15:00:00Z"
    }
)
```

### 4. context-broker-get-contexts
**Purpose:** Retrieves all available contexts from the contexts database

**Use Case:** Discovering available knowledge bases

**Parameters:** None

**Example:**
```python
from backend.app.mcp.context_studio_tools import create_get_contexts

tool_call = create_get_contexts()
```

### 5. context-broker-get-context-metadata
**Purpose:** Retrieves context metadata including sources, connected systems, and ingested documents

**Use Case:** Understanding what data is available in a context

**Parameters:**
- `context_id` (required): Context ID to retrieve metadata for

**Example:**
```python
from backend.app.mcp.context_studio_tools import create_get_context_metadata

tool_call = create_get_context_metadata(
    context_id="ctx_b4043773b9c6"
)
```

### 6. context-broker-graph-query
**Purpose:** Executes graph-based queries to traverse relationships and find connected context

**Use Case:** Finding related documents through knowledge graph relationships

**Parameters:**
- `context_id` (required): Context ID
- `start_node` (required): Starting node ID for graph traversal
- `relationship_types` (optional): Filter by relationship types
- `max_depth` (optional, default=1): Maximum traversal depth (1-3)
- `limit` (optional, default=5): Maximum results (1-20)

**IMPORTANT:** Use `max_depth=1` and `limit=5` to avoid client timeouts. Operations with default values may take 60+ seconds.

**Example:**
```python
from backend.app.mcp.context_studio_tools import create_graph_query

tool_call = create_graph_query(
    context_id="ctx_b4043773b9c6",
    start_node="doc-12345",
    relationship_types=["references", "depends_on"],
    max_depth=1,  # Safe depth
    limit=5  # Safe limit
)
```

### 7. context-broker-hybrid-query
**Purpose:** Combines semantic similarity and graph relationships for comprehensive context retrieval

**Use Case:** Best option for migration copilot - finds both semantically similar and related content

**Parameters:**
- `context_id` (required): Context ID
- `query` (required): Search query
- `vector_weight` (optional, default=0.5): Weight for vector similarity (0.0-1.0)
- `graph_weight` (optional, default=0.5): Weight for graph relationships (0.0-1.0)
- `max_depth` (optional, default=1): Graph traversal depth (1-3)
- `limit` (optional, default=10): Maximum results (1-50)

**Example:**
```python
from backend.app.mcp.context_studio_tools import create_hybrid_query

tool_call = create_hybrid_query(
    context_id="ctx_b4043773b9c6",
    query="legacy application migration strategy",
    vector_weight=0.6,  # Favor semantic similarity
    graph_weight=0.4,   # Include related context
    max_depth=1,
    limit=20
)
```

## Integration with MCP Connector

### New Methods Added to MCPConnector

```python
class MCPConnector:
    async def call_tool(
        self,
        tool_call: ContextStudioToolCall,
        request_id: Optional[int] = None
    ) -> ContextStudioToolResponse:
        """Call any Context Studio MCP tool"""
        pass
    
    async def vector_search(
        self,
        context_id: str,
        query: str,
        limit: int = 10,
        threshold: Optional[float] = None
    ) -> List[Document]:
        """Convenience method for vector search"""
        pass
    
    async def hybrid_search(
        self,
        context_id: str,
        query: str,
        vector_weight: float = 0.5,
        graph_weight: float = 0.5,
        max_depth: int = 1,
        limit: int = 10
    ) -> List[Document]:
        """Convenience method for hybrid search (RECOMMENDED)"""
        pass
    
    async def get_context_metadata(
        self,
        context_id: str
    ) -> Dict[str, Any]:
        """Get context metadata"""
        pass
```

## Recommended Usage for Migration Copilot

### For Context Retrieval Agent

Use **hybrid search** as the primary retrieval method:

```python
# In Context Retrieval Agent
connector = MCPConnector()

documents = await connector.hybrid_search(
    context_id="ctx_b4043773b9c6",
    query="application architecture and dependencies",
    vector_weight=0.6,  # Favor semantic similarity
    graph_weight=0.4,   # Include related docs
    max_depth=1,        # Safe depth
    limit=50            # Get enough context
)
```

### For Extraction Agent

Use **vector search** for specific technical information:

```python
# In Extraction Agent
documents = await connector.vector_search(
    context_id="ctx_b4043773b9c6",
    query="database schema and data models",
    limit=30,
    threshold=0.7  # High confidence matches only
)
```

### For Migration Planning Agent

Use **graph query** to find related migration artifacts:

```python
# In Migration Planning Agent
from backend.app.mcp.context_studio_tools import create_graph_query

tool_call = create_graph_query(
    context_id="ctx_b4043773b9c6",
    start_node="migration-plan-template",
    relationship_types=["similar_to", "references"],
    max_depth=1,
    limit=10
)

response = await connector.call_tool(tool_call)
```

### For Posting Events

Notify Context Studio when artifacts are generated:

```python
# After generating migration plan
from backend.app.mcp.context_studio_tools import create_post_event

tool_call = create_post_event(
    context_id="ctx_b4043773b9c6",
    event_type="migration_plan_generated",
    source="migration-copilot",
    payload={
        "project_id": project_id,
        "plan_url": plan_url,
        "status": "ready_for_review"
    }
)

await connector.call_tool(tool_call)
```

## Configuration

### Environment Variables

```env
# Context Studio Configuration
MCP_GATEWAY_URL=https://servicesessentials.ibm.com/mcp-gateway/service/gateway/servers/8ccdd203bdee4014b08e82eedb6046e2/mcp
MCP_GATEWAY_TOKEN=your_bearer_token
MCP_API_KEY=your_api_key
MCP_TIMEOUT=30
MCP_MAX_RETRIES=3

# Context ID (use as project_id)
DEFAULT_CONTEXT_ID=ctx_b4043773b9c6
```

### MCP Configuration for Bob

```json
{
  "mcpServers": {
    "context-studio": {
      "type": "streamable-http",
      "url": "https://servicesessentials.ibm.com/mcp-gateway/service/gateway/servers/8ccdd203bdee4014b08e82eedb6046e2/mcp",
      "headers": {
        "Authorization": "Bearer <mcp-gateway-token>",
        "x-api-key": "<context-studio-key>"
      },
      "disabled": false
    }
  }
}
```

## Files Created

1. **backend/app/mcp/context_studio_tools.py** (298 lines)
   - Tool definitions and parameter models
   - Helper functions for creating tool calls
   - Response parsing

2. **PHASE2_CONTEXT_STUDIO_INTEGRATION.md** (this file)
   - Complete documentation
   - Usage examples
   - Best practices

## Next Steps

1. **Test Context Studio Tools**
   - Verify connectivity with actual context ID
   - Test vector search with real queries
   - Test hybrid search for comprehensive retrieval

2. **Update Retrieval Profiles**
   - Map profiles to Context Studio tools
   - Optimize weights for different use cases
   - Add profile-specific tool selection

3. **Integrate with Agents**
   - Update Context Retrieval Agent to use hybrid search
   - Update Extraction Agent to use vector search
   - Add event posting after artifact generation

4. **Add Caching**
   - Cache Context Studio responses
   - Implement TTL-based invalidation
   - Add cache warming for common queries

5. **Add Monitoring**
   - Track tool call latencies
   - Monitor success/error rates
   - Alert on timeout issues

## Performance Considerations

### Timeout Prevention

- **Always use `max_depth=1`** for graph queries
- **Keep `limit` low** (5-20) for graph queries
- **Use vector search** for simple semantic matching
- **Use hybrid search** for comprehensive retrieval with safe defaults

### Optimal Settings

| Use Case | Tool | Vector Weight | Graph Weight | Max Depth | Limit |
|----------|------|---------------|--------------|-----------|-------|
| General Context | Hybrid | 0.6 | 0.4 | 1 | 50 |
| Technical Details | Vector | N/A | N/A | N/A | 30 |
| Related Docs | Graph | N/A | N/A | 1 | 10 |
| Comprehensive | Hybrid | 0.5 | 0.5 | 1 | 100 |

## Conclusion

The Context Studio MCP tools provide powerful semantic search and graph traversal capabilities for the migration copilot. The hybrid search tool is recommended as the primary retrieval method, combining the best of both vector similarity and graph relationships.

**Status:** ✅ Tools defined and documented, ready for integration testing