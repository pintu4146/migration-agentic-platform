# IBM Context Studio MCP Integration Skill

## Overview

This document captures the knowledge and patterns for integrating with IBM Context Studio through the Model Context Protocol (MCP) Gateway.

**Reference Repository**: https://github.com/IBM/mcp-context-forge

## Key Concepts

### 1. MCP Protocol

IBM Context Studio uses **JSON-RPC 2.0** protocol, NOT REST endpoints.

**Correct Pattern:**
```python
payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",  # or "resources/list", "tools/call"
    "params": {...}
}

response = await client.post(gateway_url, json=payload, headers=headers)
```

**Wrong Pattern (causes 404):**
```python
# DON'T DO THIS - No REST endpoints
response = await client.post(f"{gateway_url}/search", json=params)
```

### 2. Authentication

IBM Context Studio requires **dual authentication**:

1. **Bearer Token** (MCP Gateway access)
   - Header: `Authorization: Bearer {token}`
   - Obtained from MCP Gateway

2. **API Key** (Context Studio access)
   - Header: `x-api-key: {api_key}`
   - JWT token containing `contextId`

**Example Headers:**
```python
headers = {
    "Authorization": f"Bearer {gateway_token}",
    "x-api-key": api_key,
    "Content-Type": "application/json",
    "Accept": "application/json"
}
```

### 3. Context ID

The `contextId` is embedded in the MCP_API_KEY JWT token.

**Decode to extract:**
```python
import jwt
decoded = jwt.decode(api_key, options={"verify_signature": False})
context_id = decoded["contextId"]  # e.g., "ctx_b4043773b9c6"
```

**Usage:**
- Use `context_id` as `project_id` in API requests
- NOT arbitrary values like "proj_abc123"

## MCP Methods

### 1. initialize (Health Check)

**Purpose**: Verify MCP Gateway connectivity and capabilities

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {
      "name": "migration-copilot",
      "version": "1.0.0"
    }
  }
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {...},
    "serverInfo": {...}
  }
}
```

### 2. resources/list (Retrieve Context)

**Purpose**: List available resources/documents in the context

**Request:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "resources/list",
  "params": {}
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "resources": [
      {
        "uri": "context://...",
        "name": "Resource Name",
        "description": "Resource description",
        "mimeType": "text/plain"
      }
    ]
  }
}
```

### 3. tools/call (Execute Context Studio Tools)

**Purpose**: Execute Context Studio tools for advanced queries

**Available Tools:**
1. `context-broker-vector-query` - Semantic search
2. `context-broker-graph-query` - Graph traversal
3. `context-broker-hybrid-query` - Vector + Graph (RECOMMENDED)
4. `context-broker-get-context-schema` - Ontology schemas
5. `context-broker-post-events` - Event notifications
6. `context-broker-get-contexts` - List contexts
7. `context-broker-get-context-metadata` - Context metadata

**Example - Hybrid Query:**
```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "context-broker-hybrid-query",
    "arguments": {
      "contextId": "ctx_b4043773b9c6",
      "query": "migration architecture",
      "limit": 10,
      "max_depth": 1
    }
  }
}
```

## Common Pitfalls

### ❌ Pitfall 1: Using REST Endpoints

**Problem:**
```python
response = await client.post(f"{gateway_url}/search", json=params)
# Results in: 404 Not Found
```

**Solution:**
```python
payload = {"jsonrpc": "2.0", "method": "resources/list", ...}
response = await client.post(gateway_url, json=payload)
```

### ❌ Pitfall 2: Wrong Project ID

**Problem:**
```python
project_id = "proj_abc123"  # Arbitrary value
# Results in: No resources found or permission errors
```

**Solution:**
```python
# Extract from API key or use configured value
project_id = "ctx_b4043773b9c6"  # From JWT token
```

### ❌ Pitfall 3: Missing x-api-key Header

**Problem:**
```python
headers = {"Authorization": f"Bearer {token}"}
# Results in: 401 Unauthorized
```

**Solution:**
```python
headers = {
    "Authorization": f"Bearer {token}",
    "x-api-key": api_key  # Required!
}
```

### ❌ Pitfall 4: Unbounded Graph Queries

**Problem:**
```python
# No depth limit - can timeout
arguments = {"contextId": ctx, "query": "..."}
```

**Solution:**
```python
# Always set limits
arguments = {
    "contextId": ctx,
    "query": "...",
    "max_depth": 1,  # Prevent deep traversal
    "limit": 5       # Limit results
}
```

## Implementation Patterns

### Pattern 1: Health Check

```python
async def health_check(self) -> bool:
    """Check MCP Gateway health using initialize method."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "app", "version": "1.0.0"}
        }
    }
    
    response = await self.client.post(
        self.gateway_url,
        json=payload,
        headers=self._get_headers()
    )
    
    data = response.json()
    return "result" in data
```

### Pattern 2: Resource Retrieval

```python
async def retrieve_resources(self, context_id: str) -> List[Dict]:
    """Retrieve resources from Context Studio."""
    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "resources/list",
        "params": {}
    }
    
    response = await self.client.post(
        self.gateway_url,
        json=payload,
        headers=self._get_headers()
    )
    
    data = response.json()
    
    if "error" in data:
        raise MCPError(f"MCP error: {data['error']['message']}")
    
    return data.get("result", {}).get("resources", [])
```

### Pattern 3: Tool Execution

```python
async def execute_tool(
    self,
    tool_name: str,
    arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute a Context Studio tool."""
    payload = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    response = await self.client.post(
        self.gateway_url,
        json=payload,
        headers=self._get_headers()
    )
    
    data = response.json()
    
    if "error" in data:
        raise MCPError(f"Tool error: {data['error']['message']}")
    
    return data.get("result", {})
```

## Configuration

### Environment Variables

```env
# MCP Gateway URL (includes server ID)
MCP_GATEWAY_URL=https://servicesessentials.ibm.com/mcp-gateway/service/gateway/servers/{server_id}/mcp

# Bearer token for MCP Gateway
MCP_GATEWAY_TOKEN=eyJhbGci...

# API key for Context Studio (contains contextId)
MCP_API_KEY=eyJhbGci...

# Timeouts and limits
MCP_TIMEOUT=30
MCP_MAX_RETRIES=3
MCP_RATE_LIMIT_PER_MINUTE=60

# Default context ID (extracted from API key)
DEFAULT_CONTEXT_ID=ctx_b4043773b9c6
```

### Pydantic Settings

```python
class Settings(BaseSettings):
    mcp_gateway_url: str
    mcp_gateway_token: str
    mcp_api_key: str
    mcp_timeout: int = 30
    mcp_max_retries: int = 3
    default_context_id: str = "ctx_b4043773b9c6"
```

## Error Handling

### JSON-RPC Error Response

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32600,
    "message": "Invalid Request",
    "data": {...}
  }
}
```

### Error Codes

- `-32700`: Parse error
- `-32600`: Invalid Request
- `-32601`: Method not found
- `-32602`: Invalid params
- `-32603`: Internal error

### Handling Pattern

```python
data = response.json()

if "error" in data:
    error = data["error"]
    code = error.get("code")
    message = error.get("message", "Unknown error")
    
    if code == -32601:
        raise MCPError(f"Method not found: {message}")
    elif code == -32602:
        raise MCPError(f"Invalid parameters: {message}")
    else:
        raise MCPError(f"MCP error ({code}): {message}")

if "result" not in data:
    raise MCPError("No result in response")

return data["result"]
```

## Best Practices

### 1. Always Use JSON-RPC 2.0

✅ **DO:**
```python
payload = {"jsonrpc": "2.0", "id": 1, "method": "...", "params": {...}}
```

❌ **DON'T:**
```python
# No REST endpoints
url = f"{gateway_url}/api/search"
```

### 2. Include Both Auth Headers

✅ **DO:**
```python
headers = {
    "Authorization": f"Bearer {gateway_token}",
    "x-api-key": api_key
}
```

❌ **DON'T:**
```python
headers = {"Authorization": f"Bearer {gateway_token}"}  # Missing x-api-key
```

### 3. Use Correct Context ID

✅ **DO:**
```python
context_id = settings.default_context_id  # From JWT token
```

❌ **DON'T:**
```python
context_id = "proj_abc123"  # Arbitrary value
```

### 4. Set Query Limits

✅ **DO:**
```python
arguments = {
    "contextId": ctx,
    "query": "...",
    "max_depth": 1,
    "limit": 5
}
```

❌ **DON'T:**
```python
arguments = {"contextId": ctx, "query": "..."}  # No limits
```

### 5. Handle JSON-RPC Errors

✅ **DO:**
```python
if "error" in data:
    raise MCPError(data["error"]["message"])
if "result" not in data:
    raise MCPError("No result")
return data["result"]
```

❌ **DON'T:**
```python
return data["result"]  # May crash if error
```

## Testing

### Test Health Check

```bash
curl -X POST https://servicesessentials.ibm.com/mcp-gateway/.../mcp \
  -H "Authorization: Bearer ${MCP_GATEWAY_TOKEN}" \
  -H "x-api-key: ${MCP_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "test", "version": "1.0.0"}
    }
  }'
```

### Test Resource List

```bash
curl -X POST https://servicesessentials.ibm.com/mcp-gateway/.../mcp \
  -H "Authorization: Bearer ${MCP_GATEWAY_TOKEN}" \
  -H "x-api-key: ${MCP_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "resources/list",
    "params": {}
  }'
```

### Test Hybrid Query

```bash
curl -X POST https://servicesessentials.ibm.com/mcp-gateway/.../mcp \
  -H "Authorization: Bearer ${MCP_GATEWAY_TOKEN}" \
  -H "x-api-key: ${MCP_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "context-broker-hybrid-query",
      "arguments": {
        "contextId": "ctx_b4043773b9c6",
        "query": "migration",
        "limit": 5,
        "max_depth": 1
      }
    }
  }'
```

## Troubleshooting

### Issue: 404 Not Found

**Cause**: Using REST endpoints instead of JSON-RPC

**Solution**: Use JSON-RPC 2.0 protocol with proper method names

### Issue: 401 Unauthorized

**Cause**: Missing or invalid authentication headers

**Solution**: Include both `Authorization` and `x-api-key` headers

### Issue: Empty Results

**Cause**: Wrong context ID or no resources in context

**Solution**: Use correct context ID from API key JWT token

### Issue: Timeout

**Cause**: Unbounded graph queries or slow network

**Solution**: Set `max_depth` and `limit` parameters

### Issue: Rate Limiting

**Cause**: Too many requests

**Solution**: Implement exponential backoff and respect rate limits

## References

- **IBM MCP Context Forge**: https://github.com/IBM/mcp-context-forge
- **MCP Specification**: https://modelcontextprotocol.io/
- **JSON-RPC 2.0**: https://www.jsonrpc.org/specification
- **Context Studio Docs**: IBM internal documentation

## Version History

- **v1.0** (2026-05-25): Initial skill document
  - MCP protocol patterns
  - Authentication requirements
  - Common pitfalls and solutions
  - Implementation patterns
  - Testing examples

---

**Last Updated**: 2026-05-25  
**Maintainer**: Migration Copilot Team  
**Status**: Active