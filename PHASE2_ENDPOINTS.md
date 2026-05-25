# Phase 2: MCP Connector - API Endpoints Documentation

## Overview

Phase 2 implements the MCP (Model Context Protocol) connector module for IBM Context Studio Gateway integration. This document lists all available endpoints and how to test them.

## Base URL

```
http://127.0.0.1:8000
```

## Authentication

All MCP endpoints require proper configuration in `.env`:
```
MCP_GATEWAY_URL=https://servicesessentials.ibm.com/mcp-gateway/service/gateway/servers/{server_id}/mcp
MCP_BEARER_TOKEN=your_bearer_token
MCP_API_KEY=your_api_key
```

---

## Phase 2 Endpoints

### 1. Health Check (Root)

**Endpoint:** `GET /`

**Description:** Basic health check for the FastAPI application

**Response:**
```json
{
  "status": "healthy",
  "service": "Migration Agent Orchestration API",
  "version": "0.1.0",
  "phase": "Phase 2: MCP Connector"
}
```

**cURL:**
```bash
curl http://127.0.0.1:8000/
```

---

### 2. MCP Gateway Health Check

**Endpoint:** `GET /mcp/health`

**Description:** Check connectivity to IBM Context Studio MCP Gateway

**Response (Success):**
```json
{
  "status": "healthy",
  "gateway_url": "https://servicesessentials.ibm.com/mcp-gateway/...",
  "timestamp": "2026-05-25T15:30:00.000Z"
}
```

**Response (Error):**
```json
{
  "status": "unhealthy",
  "gateway_url": "https://servicesessentials.ibm.com/mcp-gateway/...",
  "error": "Connection timeout",
  "timestamp": "2026-05-25T15:30:00.000Z"
}
```

**cURL:**
```bash
curl http://127.0.0.1:8000/mcp/health
```

---

### 3. Retrieve Context

**Endpoint:** `POST /mcp/retrieve`

**Description:** Retrieve context from MCP Gateway using a retrieval profile

**Request Body:**
```json
{
  "profile_type": "context_retrieval",
  "query": "application architecture",
  "custom_profile": null
}
```

**Profile Types:**
- `context_retrieval` - General context gathering
- `extraction` - Technical stack extraction
- `questionnaire` - Gap analysis
- `planning` - Migration planning
- `review` - Review and validation

**Response:**
```json
{
  "documents": [
    {
      "id": "page-12345",
      "title": "Application Architecture",
      "content": "...",
      "source": "confluence",
      "type": "page",
      "url": "https://...",
      "metadata": {
        "author": "john.doe@ibm.com",
        "created_at": "2026-01-15T10:00:00Z",
        "updated_at": "2026-05-20T14:30:00Z",
        "space": "TECH",
        "labels": ["architecture", "microservices"],
        "word_count": 1500,
        "has_attachments": true
      },
      "confidence": 0.95,
      "evidence_refs": ["section-intro", "diagram-1"]
    }
  ],
  "total_count": 1,
  "profile_used": "context_retrieval",
  "retrieved_at": "2026-05-25T15:30:00.000Z"
}
```

**cURL:**
```bash
curl -X POST http://127.0.0.1:8000/mcp/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "profile_type": "context_retrieval",
    "query": "application architecture"
  }'
```

---

### 4. List Available Profiles

**Endpoint:** `GET /mcp/profiles`

**Description:** List all predefined retrieval profiles

**Response:**
```json
{
  "profiles": [
    {
      "type": "context_retrieval",
      "description": "General context gathering from all sources",
      "source_types": ["page", "attachment", "comment"],
      "max_results": 50
    },
    {
      "type": "extraction",
      "description": "Technical stack and architecture extraction",
      "source_types": ["page", "attachment"],
      "max_results": 100
    },
    {
      "type": "questionnaire",
      "description": "Gap analysis and missing information",
      "source_types": ["page"],
      "max_results": 30
    },
    {
      "type": "planning",
      "description": "Migration planning and strategy",
      "source_types": ["page", "attachment"],
      "max_results": 75
    },
    {
      "type": "review",
      "description": "Review and validation",
      "source_types": ["page"],
      "max_results": 40
    }
  ]
}
```

**cURL:**
```bash
curl http://127.0.0.1:8000/mcp/profiles
```

---

### 5. Get Specific Profile

**Endpoint:** `GET /mcp/profiles/{profile_type}`

**Description:** Get configuration for a specific profile

**Path Parameters:**
- `profile_type`: One of `context_retrieval`, `extraction`, `questionnaire`, `planning`, `review`

**Response:**
```json
{
  "source_types": ["page", "attachment"],
  "content_types": ["text/html", "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
  "keyword_filters": ["architecture", "technical", "stack", "dependencies"],
  "section_filters": ["technical", "architecture", "infrastructure"],
  "max_results": 100,
  "freshness_days": 180,
  "include_attachments": true,
  "include_comments": false
}
```

**cURL:**
```bash
curl http://127.0.0.1:8000/mcp/profiles/extraction
```

---

### 6. Validate Custom Profile

**Endpoint:** `POST /mcp/profiles/validate`

**Description:** Validate a custom retrieval profile configuration

**Request Body:**
```json
{
  "source_types": ["page"],
  "content_types": ["text/html"],
  "keyword_filters": ["custom", "keywords"],
  "max_results": 25,
  "freshness_days": 90
}
```

**Response (Valid):**
```json
{
  "valid": true,
  "message": "Profile configuration is valid"
}
```

**Response (Invalid):**
```json
{
  "valid": false,
  "errors": [
    "max_results must be between 1 and 1000",
    "freshness_days must be positive"
  ]
}
```

**cURL:**
```bash
curl -X POST http://127.0.0.1:8000/mcp/profiles/validate \
  -H "Content-Type: application/json" \
  -d '{
    "source_types": ["page"],
    "max_results": 25,
    "freshness_days": 90
  }'
```

---

## Interactive API Documentation

FastAPI provides interactive API documentation:

### Swagger UI
```
http://127.0.0.1:8000/docs
```

### ReDoc
```
http://127.0.0.1:8000/redoc
```

### OpenAPI Schema
```
http://127.0.0.1:8000/openapi.json
```

---

## Testing the Endpoints

### 1. Start the Server

```bash
cd backend
venv\Scripts\activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Test Basic Health

```bash
curl http://127.0.0.1:8000/
```

### 3. Test MCP Health (requires valid credentials)

```bash
curl http://127.0.0.1:8000/mcp/health
```

### 4. List Profiles

```bash
curl http://127.0.0.1:8000/mcp/profiles
```

### 5. Get Specific Profile

```bash
curl http://127.0.0.1:8000/mcp/profiles/extraction
```

### 6. Test Context Retrieval (requires valid credentials and MCP access)

```bash
curl -X POST http://127.0.0.1:8000/mcp/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "profile_type": "context_retrieval",
    "query": "test query"
  }'
```

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK` - Success
- `400 Bad Request` - Invalid input
- `401 Unauthorized` - Missing or invalid credentials
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error
- `502 Bad Gateway` - MCP Gateway error
- `503 Service Unavailable` - MCP Gateway unavailable
- `504 Gateway Timeout` - MCP Gateway timeout

Error response format:
```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Configuration

Ensure your `.env` file has these settings:

```env
# MCP Gateway Configuration
MCP_GATEWAY_URL=https://servicesessentials.ibm.com/mcp-gateway/service/gateway/servers/{server_id}/mcp
MCP_BEARER_TOKEN=your_bearer_token_here
MCP_API_KEY=your_api_key_here
MCP_TIMEOUT=30
MCP_MAX_RETRIES=3

# LLM Provider (for future phases)
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key

# LangSmith Tracing
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=migration-agent-poc
LANGSMITH_TRACING=true
```

---

## Phase 2 Implementation Summary

**Files Created:**
1. `backend/app/mcp/__init__.py` - Module exports
2. `backend/app/mcp/models.py` - Data models (171 lines)
3. `backend/app/mcp/profiles.py` - Retrieval profiles (283 lines)
4. `backend/app/mcp/connector.py` - MCP HTTP client (476 lines)
5. `backend/app/api/__init__.py` - API router exports
6. `backend/app/api/mcp.py` - MCP REST endpoints (243 lines)
7. `backend/tests/test_mcp.py` - Test suite (201 lines)

**Total:** ~1,400 lines of production-quality code

**Key Features:**
- ✅ IBM Context Studio MCP Gateway integration
- ✅ Dual authentication (Bearer + API key)
- ✅ 5 predefined retrieval profiles
- ✅ Custom profile support with validation
- ✅ Automatic retry with exponential backoff
- ✅ Document normalization with confidence scoring
- ✅ Evidence reference tracking
- ✅ Comprehensive error handling
- ✅ Full async/await support
- ✅ OpenAPI documentation
- ✅ Test suite

---

## Next Steps

**Phase 3: LangGraph Orchestration**
- Shared state management
- Transaction-style state commits
- Node transitions and checkpointing
- Agent workflow implementation

**To proceed to Phase 3, confirm Phase 2 is working correctly.**