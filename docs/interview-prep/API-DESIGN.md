# API Design — Complete Guide for Senior Engineers

**Scalable, Production-Grade REST API Principles**
Based on real patterns from IBM Migration Copilot — then extended to industry best practices.

---

## Table of Contents

1. [Foundations](#foundations)
2. [Resource Naming & URL Structure](#resource-naming)
3. [Request & Response Contracts](#request-response)
4. [HTTP Status Codes](#status-codes)
5. [Versioning Strategies](#versioning)
6. [Authentication & Authorization](#auth)
7. [Real-time: SSE vs WebSocket vs Polling](#real-time)
8. [Error Handling](#error-handling)
9. [Pagination, Filtering & Sorting](#pagination)
10. [Streaming & File Uploads](#streaming)
11. [Rate Limiting & Throttling](#rate-limiting)
12. [Idempotency](#idempotency)
13. [CORS & Security Headers](#security)
14. [API Contracts with Pydantic](#pydantic)
15. [Scalability Patterns](#scalability)
16. [Testing APIs](#testing)
17. [Interview Q&A](#interview-qa)

---

## 1. Foundations {#foundations}

### REST Constraints (What REST Actually Means)

REST is an architectural style with 6 constraints — most APIs only implement 3.

| Constraint | Description | This codebase |
|---|---|---|
| **Client-Server** | UI and API are separate | ✅ React frontend + FastAPI backend |
| **Stateless** | Each request is self-contained | ✅ State stored in Redis, not server memory |
| **Cacheable** | Responses declare cacheability | ⚠️ `Cache-Control: no-cache` on SSE stream |
| **Uniform Interface** | Consistent resource naming | ✅ `/api/projects`, `/api/documents` |
| **Layered System** | Client doesn't know about internals | ✅ Vite proxy hides backend from frontend |
| **Code on Demand** | Optional: send executable code | ❌ Not used (rarely is) |

**Interview tip:** "Most REST APIs are really just HTTP APIs. True REST includes HATEOAS (links in responses). Most teams call their HTTP APIs 'REST' informally."

### HTTP Methods — The Right Semantics

```
GET    /projects          → List (safe, idempotent, cacheable)
GET    /projects/{id}     → Retrieve one (safe, idempotent, cacheable)
POST   /projects          → Create (not idempotent, not cacheable)
PUT    /projects/{id}     → Full replace (idempotent)
PATCH  /projects/{id}     → Partial update (idempotent)
DELETE /projects/{id}     → Delete (idempotent)

Safe     = no side effects (GET, HEAD, OPTIONS)
Idempotent = calling N times = calling once (GET, PUT, DELETE, OPTIONS)
```

**📂 See in codebase:**
- [`backend/app/api/projects.py` (L64-297)](../../backend/app/api/projects.py) — `POST /create`, `GET /list`, `GET /{id}`, `DELETE /{id}`
- [`backend/app/api/documents.py` (L71-334)](../../backend/app/api/documents.py) — `POST /upload`, `GET /list`, `DELETE /{id}`

---

## 2. Resource Naming & URL Structure {#resource-naming}

### The Rules

```
✅ Nouns, not verbs
✅ Plural for collections
✅ Lowercase, hyphens not underscores
✅ Hierarchical (nested only when makes sense)
✅ IDs in path for specific resources
✅ Query params for filters/search

❌ /getProjects (verb in URL)
❌ /project (singular)
❌ /Project_List (uppercase + underscore)
```

### Real Examples from This Codebase

```
# Resources
GET    /api/projects              → list all projects
POST   /api/projects/create       → create project (note: /create is debatable)
GET    /api/projects/{project_id} → get one project
DELETE /api/projects/{project_id} → delete project

GET    /api/documents/list/{project_id} → list documents in project
POST   /api/documents/upload            → upload document
DELETE /api/documents/{document_id}     → delete document

POST   /api/orchestration/start    → start workflow
POST   /api/orchestration/execute  → run workflow
POST   /api/orchestration/resume   → resume from pause
POST   /api/orchestration/reset    → reset workflow
GET    /api/orchestration/state/{project_id}   → get current state
GET    /api/orchestration/stream/{project_id}  → SSE stream

GET    /mcp/health                   → health check
POST   /mcp/retrieve                 → retrieve context
GET    /mcp/profiles                 → list profiles
GET    /mcp/profiles/{profile_type}  → get one profile
POST   /mcp/profiles/validate        → validate profile
```

**📂 See router prefixes:**
- [`backend/app/api/projects.py` (L18)](../../backend/app/api/projects.py) — `prefix="/api/projects"`
- [`backend/app/api/documents.py` (L26)](../../backend/app/api/documents.py) — `prefix="/api/documents"`
- [`backend/app/api/orchestration.py` (L24)](../../backend/app/api/orchestration.py) — `prefix="/api/orchestration"`
- [`backend/app/api/mcp.py` (L26)](../../backend/app/api/mcp.py) — `prefix="/mcp"`

### Debatable Patterns in This Codebase

| URL Pattern | Problem | Better Alternative |
|---|---|---|
| `POST /projects/create` | Verb in URL | `POST /projects` (POST itself implies create) |
| `GET /documents/list/{id}` | Verb "list" in URL | `GET /documents?project_id={id}` |
| `POST /orchestration/start` | Verb in URL | `POST /workflows` (starts a workflow resource) |

**Why this is still OK:** In practice, RPC-style endpoints (`/start`, `/execute`, `/resume`) are common for actions that don't map cleanly to CRUD. FastAPI's design encourages this.

### Nested Resources (When to Use)

```
# ✅ Use nesting when the resource only exists in context of parent
GET /projects/{project_id}/documents
GET /projects/{project_id}/state
GET /projects/{project_id}/workflow/stream

# ❌ Don't nest too deep (hard to read, over-coupled)
GET /orgs/{id}/projects/{id}/workflows/{id}/agents/{id}/output  ← too deep

# Rule: max 2 levels of nesting
```

---

## 3. Request & Response Contracts {#request-response}

### Pydantic Models as Contracts

Every endpoint in this codebase uses separate request and response models — not raw dicts.

```python
# ✅ This codebase pattern: explicit request + response models

class StartWorkflowRequest(BaseModel):
    project_id: str = Field(description="Unique project identifier")
    mcp_profile: str = Field(
        default="context_retrieval_profile",
        description="MCP retrieval profile name"
    )
    query: Optional[str] = Field(
        default=None,
        description="Optional search query"
    )

class StartWorkflowResponse(BaseModel):
    project_id: str
    state_version: int
    phase: str
    message: str

@router.post("/start", response_model=StartWorkflowResponse)
async def start_workflow(request: StartWorkflowRequest) -> StartWorkflowResponse:
    ...
```

**📂 See in codebase:**
- All request/response models: [`backend/app/api/orchestration.py` (L29-118)](../../backend/app/api/orchestration.py)
- Shared schemas: [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py)

### Response Envelope Pattern

Wrap responses in a consistent envelope for scalability:

```python
# ❌ Raw data (hard to extend without breaking clients)
return {"project_id": "abc", "name": "My Project"}

# ✅ Envelope (can add meta, pagination, links without breaking)
return {
    "data": {"project_id": "abc", "name": "My Project"},
    "meta": {"version": "1.0", "timestamp": "2024-..."},
    "links": {"self": "/api/projects/abc"}
}
```

**This codebase uses flat responses** (no envelope) — simpler but harder to extend later without breaking clients.

### Always Return Consistent Shape

```python
# ✅ Every list endpoint: data array + total count
class DocumentListResponse(BaseModel):
    documents: List[Dict[str, Any]]  # ← consistent "data" key
    total: int                        # ← consistent "total" key

# ✅ Every delete endpoint: consistent confirmation
return {
    "status": "success",
    "message": "Deleted 5 chunks",
    "document_id": document_id
}
```

**📂 See in codebase:**
- [`backend/app/api/documents.py` (L44-61)](../../backend/app/api/documents.py) — `DocumentListResponse`, `DocumentSearchResponse`
- [`backend/app/api/projects.py` (L58-62)](../../backend/app/api/projects.py) — `ProjectListResponse`

---

## 4. HTTP Status Codes {#status-codes}

### The Full Map

```
2xx — Success
  200 OK             → GET, PUT, PATCH, DELETE (with body)
  201 Created        → POST that creates a resource
  202 Accepted       → Async operation started (not yet done)
  204 No Content     → DELETE (no body)

3xx — Redirect
  301 Moved Permanently → Permanent URL change
  302 Found             → Temporary redirect
  304 Not Modified      → Cached response still valid

4xx — Client Error
  400 Bad Request       → Malformed request / validation failure
  401 Unauthorized      → Not authenticated (missing/invalid token)
  403 Forbidden         → Authenticated but not permitted
  404 Not Found         → Resource doesn't exist
  405 Method Not Allowed → GET on /create, etc.
  409 Conflict          → State conflict (duplicate, version mismatch)
  410 Gone              → Resource permanently deleted
  413 Payload Too Large → File size exceeds limit
  422 Unprocessable     → Syntactically valid but semantically wrong
  429 Too Many Requests → Rate limit exceeded

5xx — Server Error
  500 Internal Server Error → Unexpected failure
  502 Bad Gateway           → Upstream service failed
  503 Service Unavailable   → Overloaded or down for maintenance
  504 Gateway Timeout       → Upstream timed out
```

### How This Codebase Uses Status Codes

```python
# 400 — Validation error
if not file.filename:
    raise HTTPException(status_code=400, detail="Filename is required")

# 400 — Unsupported type
if not ParserFactory.is_supported(file.filename):
    raise HTTPException(status_code=400, detail=f"Unsupported: {ext}")

# 404 — Not found
if collection_name not in collection_names:
    raise HTTPException(status_code=404, detail=f"Project '{id}' not found")

# 409 — Conflict (duplicate project or version mismatch)
if collection_name in existing_collections:
    raise HTTPException(status_code=409, detail="Project already exists")

# 422 — FastAPI auto-returns for Pydantic validation failures

# 500 — Generic catch-all (with detail in dev, generic in prod)
@app.exception_handler(Exception)
async def general_handler(request, exc):
    return JSONResponse(status_code=500, content={
        "error": "Internal server error",
        "detail": str(exc) if settings.environment != "production" else None
    })

# 503 — Dependency unavailable
if _mcp_connector is None:
    raise HTTPException(status_code=503, detail="MCP connector unavailable")
```

**📂 See in codebase:**
- [`backend/app/main.py` (L113-145)](../../backend/app/main.py) — global exception handlers
- [`backend/app/api/projects.py` (L80-130)](../../backend/app/api/projects.py) — 400/409/500
- [`backend/app/api/mcp.py` (L143-160)](../../backend/app/api/mcp.py) — 400/503/500

---

## 5. Versioning Strategies {#versioning}

### Four Approaches

```
1. URL versioning     /api/v1/projects, /api/v2/projects
   Pros: Explicit, easy to debug
   Cons: URL pollution, hard to maintain multiple versions

2. Header versioning  Accept: application/vnd.api+json;version=2
   Pros: Clean URLs
   Cons: Not visible in browser, complex routing

3. Query param        GET /api/projects?version=2
   Pros: Simple to test
   Cons: Caching issues, unprofessional

4. Subdomain          v2.api.example.com/projects
   Pros: Clean separation
   Cons: DNS overhead, CORS complexity
```

**This codebase:** No versioning currently. This is fine for internal/single-team APIs.

**When to add versioning:**

```
Add /v1/ prefix if ANY of these are true:
- External clients consume your API (third parties)
- Mobile apps that can't be force-updated
- Multiple teams consuming at different cadences
- Public API with SLA guarantees
```

**How to add it without breaking existing clients:**

```python
# Option 1: URL versioning (most common)
app.include_router(v1_router, prefix="/api/v1")
app.include_router(v2_router, prefix="/api/v2")
# Keep /api (no version) pointing to v1 for backwards compat

# Option 2: Header-based routing
@app.middleware("http")
async def version_routing(request: Request, call_next):
    version = request.headers.get("API-Version", "v1")
    request.state.api_version = version
    return await call_next(request)
```

---

## 6. Authentication & Authorization {#auth}

### Common Patterns

```
API Key       → X-API-Key: abc123
              Simple, stateless, good for service-to-service

Bearer Token  → Authorization: Bearer <jwt>
              Most common for user-facing APIs
              JWT contains claims (user_id, roles, expiry)

OAuth2        → Authorization Code flow for third parties
              Complex but industry standard for delegated access

mTLS          → Mutual TLS certificates
              For internal microservices, very secure
```

**This codebase (MCP Gateway):**

```python
# backend/app/config.py
mcp_gateway_token: Optional[str]  # Bearer token
mcp_api_key: Optional[str]        # x-api-key header

# backend/app/mcp/connector.py — headers sent to gateway
headers = {
    "Authorization": f"Bearer {self.gateway_token}",
    "x-api-key": self.api_key,
    "Content-Type": "application/json"
}
```

**Adding JWT Auth to FastAPI (production-hardened pattern):**

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

# Production constants — load from env, never hardcode
SECRET_KEY = os.environ["JWT_SECRET_KEY"]
EXPECTED_AUDIENCE = os.environ["JWT_AUDIENCE"]    # e.g. "migration-copilot-api"
EXPECTED_ISSUER = os.environ["JWT_ISSUER"]        # e.g. "https://auth.example.com"

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Dependency: validate JWT and return user claims"""
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"],
            # ⚠️ Production MUST validate audience and issuer:
            # Without these, any token signed with the same key from a
            # *different* service is accepted — a critical security gap.
            audience=EXPECTED_AUDIENCE,   # "aud" claim in JWT
            issuer=EXPECTED_ISSUER,       # "iss" claim in JWT
        )
        return payload  # {user_id, role, exp, aud, iss}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Invalid token audience")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="Invalid token issuer")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Use as dependency
@router.get("/projects/{id}")
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user)  # ← JWT required
):
    # current_user = {user_id, role, exp}
    if current_user["role"] not in ["admin", "viewer"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    ...
```

> **Why `audience` and `issuer` matter:** A JWT is just a signed JSON blob.
> Without `audience` validation, a token issued for your *staging* environment
> is accepted in *production*. Without `issuer` validation, any token signed
> with the same key from a *sibling service* is accepted. Both checks are a
> single-line addition but close a class of privilege-escalation attacks.

### RBAC (Role-Based Access Control)

```python
# Define roles
class Role(str, Enum):
    ADMIN = "admin"      # Can do everything
    ANALYST = "analyst"  # Can run workflows, view results
    VIEWER = "viewer"    # Can only view results

# Permission checker
def require_role(*roles: Role):
    """Dependency factory for role-based access"""
    async def check_role(user: dict = Depends(get_current_user)):
        if user["role"] not in [r.value for r in roles]:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user
    return check_role

# Apply to endpoints
@router.delete("/projects/{id}")
async def delete_project(
    project_id: str,
    user: dict = Depends(require_role(Role.ADMIN))  # Admins only
):
    ...

@router.get("/projects/{id}/state")
async def get_state(
    project_id: str,
    user: dict = Depends(require_role(Role.ADMIN, Role.ANALYST, Role.VIEWER))
):
    ...
```

---

## 7. Real-Time: SSE vs WebSocket vs Polling {#real-time}

### Comparison Table

| Feature | Polling | SSE | WebSocket |
|---|---|---|---|
| Direction | Pull (client asks) | Push (server sends) | Bidirectional |
| Protocol | HTTP | HTTP | WS (upgrade) |
| Reconnect | Manual | Auto (browser) | Manual |
| Proxy friendly | ✅ Always | ✅ Usually | ⚠️ Sometimes |
| Load balancer | ✅ Stateless | ⚠️ Sticky or shared | ❌ Sticky required |
| Latency | High (interval) | Low (push) | Very low |
| Complexity | Low | Low | High |
| Best for | Background sync | One-way updates | Chat, games |

### SSE Implementation in This Codebase

```python
# backend/app/api/orchestration.py (L434-559)

@router.get("/stream/{project_id}")
async def stream_workflow_state(project_id: str):
    
    async def event_generator():
        last_phase = None
        
        # Poll Redis for state changes
        while True:
            try:
                await asyncio.sleep(0.5)
                updated_state = await state_manager.get_state(project_id)
                
                if current_phase != last_phase:
                    # Named event: phase_transition
                    yield f"event: phase_transition\n"
                    yield f"data: {json.dumps(phase_event)}\n\n"
                
                # Named event: state_update
                yield f"event: state_update\n"
                yield f"data: {json.dumps(event_data)}\n\n"
                
            except asyncio.CancelledError:
                break  # Client disconnected
            except Exception as e:
                yield f"event: error\n"
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
```

**Key SSE rules:**
1. Each event: `event: <name>\n`, `data: <json>\n\n` (double newline ends event)
2. Named events (not generic `message`) — use `addEventListener('state_update', ...)`
3. `X-Accel-Buffering: no` — prevents nginx from holding chunks
4. Client auto-reconnects in ~3 seconds if connection drops

**Frontend consuming SSE:**

```js
// frontend/src/hooks/useWorkflowSSE.js (L54-118)

const eventSource = new EventSource(url);

// ✅ Named events — not generic onmessage
eventSource.addEventListener('state_update', (e) => {
    const data = JSON.parse(e.data);
    setState(data.state);
});

eventSource.addEventListener('phase_transition', (e) => {
    const transition = JSON.parse(e.data);
    console.log(`${transition.from_phase} → ${transition.to_phase}`);
});

// Reconnect on error
eventSource.onerror = () => {
    setIsConnected(false);
    setTimeout(() => connect(), 5000);
};
```

**📂 See in codebase:**
- Backend SSE: [`backend/app/api/orchestration.py` (L434-559)](../../backend/app/api/orchestration.py)
- Frontend hook: [`frontend/src/hooks/useWorkflowSSE.js`](../../frontend/src/hooks/useWorkflowSSE.js)

---

## 8. Error Handling {#error-handling}

### Consistent Error Response Shape

```python
# backend/app/models/schemas.py (L103-115)

class ErrorResponse(BaseModel):
    error: str       = Field(description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed info")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Usage
{
    "error": "Validation error",
    "detail": "Invalid project ID format",
    "timestamp": "2024-01-01T00:00:00Z"
}
```

### Error Hierarchy Pattern

```
HTTP Layer      → HTTPException(status_code, detail)
Domain Layer    → StateTransactionError, StateValidationError
Provider Layer  → ProviderFailureError, MCPError
Storage Layer   → RedisConnectionError, QdrantError
```

**Never leak internals in production:**

```python
# backend/app/main.py (L130-145)

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled: {exc}", exc_info=True)
    
    return JSONResponse(status_code=500, content={
        "error": "Internal server error",
        # ✅ Detail only in dev — never in production
        "detail": str(exc) if settings.environment != "production" else None
    })
```

### Error Codes for Machines

Add machine-readable error codes clients can act on:

```python
# Scalable pattern: add error_code field
class ErrorResponse(BaseModel):
    error: str
    error_code: str   # Machine-readable code
    detail: Optional[str] = None
    timestamp: datetime

# Examples
{"error": "Version mismatch", "error_code": "STATE_CONFLICT"}
{"error": "Provider unavailable", "error_code": "PROVIDER_UNAVAILABLE"}
{"error": "Rate limit exceeded", "error_code": "RATE_LIMITED"}
{"error": "Not found", "error_code": "PROJECT_NOT_FOUND"}
```

Clients can switch on `error_code` instead of parsing `detail` strings.

**📂 See in codebase:**
- Error schema: [`backend/app/models/schemas.py` (L103-115)](../../backend/app/models/schemas.py)
- Exception handlers: [`backend/app/main.py` (L113-145)](../../backend/app/main.py)
- Domain exceptions: [`backend/app/orchestration/state_manager.py` (L27-35)](../../backend/app/orchestration/state_manager.py)

---

## 9. Pagination, Filtering & Sorting {#pagination}

### Offset vs Cursor Pagination

**Offset (this codebase approach — simple)**

```python
GET /api/documents?page=2&page_size=20

# Implementation
skip = (page - 1) * page_size
items = db.query(Document).offset(skip).limit(page_size).all()

# Response
{
    "data": [...],
    "total": 150,
    "page": 2,
    "page_size": 20,
    "total_pages": 8
}
```

Pros: Simple, jump to any page.
Cons: Inconsistent with concurrent inserts (items shift).

**Cursor pagination (scalable for large datasets)**

```python
GET /api/documents?cursor=eyJpZCI6MTIzfQ==&limit=20

# Implementation
cursor_data = base64.decode(cursor)  # {id: 123, created_at: "..."}
items = db.query(Document)
    .filter(Document.id > cursor_data["id"])
    .limit(limit)
    .all()

# Response
{
    "data": [...],
    "next_cursor": "eyJpZCI6MTQzfQ==",  # Opaque, base64 encoded
    "has_more": true
}
```

Pros: Consistent, efficient for large tables.
Cons: Can't jump to page 5 directly.

**Use cursor pagination when:**
- Table > 100k rows
- Real-time data (feed, logs)
- Mobile apps (infinite scroll)

### Filtering Pattern

```python
# This codebase: basic project_id filtering via query param
GET /api/documents/list?project_id=my-project

# Scalable: typed filter params
GET /api/documents?project_id=abc&status=processed&mime_type=application/pdf

@router.get("/documents")
async def list_documents(
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    mime_type: Optional[str] = Query(None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0)
):
    ...
```

### Sorting Pattern

```python
GET /api/documents?sort_by=created_at&order=desc

@router.get("/documents")
async def list_documents(
    sort_by: str = Query(default="created_at"),
    order: Literal["asc", "desc"] = Query(default="desc"),
    ...
):
    valid_sort_fields = {"created_at", "file_name", "file_size"}
    if sort_by not in valid_sort_fields:
        raise HTTPException(400, f"Invalid sort_by: {sort_by}")
    ...
```

---

## 10. Streaming & File Uploads {#streaming}

### Multipart File Upload (This Codebase)

```python
# backend/app/api/documents.py (L71-216)

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),     # ← multipart/form-data
    project_id: str = Form("default") # ← form field
):
    # Validate
    if not file.filename:
        raise HTTPException(400, "Filename is required")
    
    if not ParserFactory.is_supported(file.filename):
        raise HTTPException(400, f"Unsupported: {ext}")
    
    # Read and process
    content = await file.read()
    
    # Write to temp file (needed for parsers that require file path)
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        tmp.write(content)
        temp_path = tmp.name
    
    try:
        parsed_doc = ParserFactory.parse_file(temp_path)
        # ... chunk, embed, store
    finally:
        os.unlink(temp_path)  # Always clean up temp file
```

**File size validation:**

```python
# backend/app/config.py
max_file_size_mb: int = Field(default=50)

# In upload endpoint — check before reading entire file
file_size = 0
chunk_size = 1024 * 1024  # 1MB
content = b""
while True:
    chunk = await file.read(chunk_size)
    if not chunk:
        break
    file_size += len(chunk)
    content += chunk
    if file_size > settings.max_file_size_mb * 1024 * 1024:
        raise HTTPException(413, "File exceeds size limit")
```

### Large Response Streaming

```python
# Stream large CSV exports instead of loading into memory
from fastapi.responses import StreamingResponse
import csv, io

@router.get("/reports/export")
async def export_report(project_id: str):
    
    async def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "fact", "confidence"])
        yield output.getvalue()
        output.truncate(0)
        output.seek(0)
        
        # Stream rows in batches
        async for batch in get_facts_batched(project_id, batch_size=100):
            for fact in batch:
                writer.writerow([fact["id"], fact["text"], fact["confidence"]])
            yield output.getvalue()
            output.truncate(0)
            output.seek(0)
    
    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=report-{project_id}.csv"}
    )
```

**📂 See in codebase:**
- Upload endpoint: [`backend/app/api/documents.py` (L71-216)](../../backend/app/api/documents.py)
- SSE stream: [`backend/app/api/orchestration.py` (L434-559)](../../backend/app/api/orchestration.py)

---

## 11. Rate Limiting & Throttling {#rate-limiting}

### Why This Matters at Scale

```
Without rate limiting:
- Single client hammers API → 100% CPU, OOM
- Scrapers eat bandwidth
- DDoS attack surface

With rate limiting:
- Fair usage across all clients
- Graceful degradation under load
- Cost control (LLM API calls)
```

### MCP Rate Limiting in This Codebase

```python
# backend/app/config.py
mcp_rate_limit_per_minute: int = Field(default=60)

# backend/app/mcp/connector.py — implemented via rate limiter
```

### Production Pattern: Redis-backed Rate Limiter

```python
from fastapi import Request
import time

async def rate_limit(
    request: Request,
    redis: Redis = Depends(get_redis),
    max_requests: int = 60,
    window_seconds: int = 60
):
    """Sliding window rate limiter"""
    client_ip = request.client.host
    key = f"rate:{client_ip}"
    now = time.time()
    
    # Sliding window using sorted set
    pipe = redis.pipeline()
    # Remove old entries
    pipe.zremrangebyscore(key, 0, now - window_seconds)
    # Count remaining
    pipe.zcard(key)
    # Add current request
    pipe.zadd(key, {str(now): now})
    # Set expiry
    pipe.expire(key, window_seconds)
    results = await pipe.execute()
    
    request_count = results[1]
    
    if request_count >= max_requests:
        # Return 429 with retry info
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(window_seconds),
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(now + window_seconds))
            }
        )
    
    # Add headers to all responses
    request.state.rate_limit_remaining = max_requests - request_count - 1

# Apply to route
@router.post("/orchestration/execute", dependencies=[Depends(rate_limit)])
async def execute_workflow(...):
    ...
```

---

## 12. Idempotency {#idempotency}

### The Problem

```
Client sends POST /start-workflow for project-123
Network glitch — client doesn't know if server received it
Client retries — now workflow started TWICE!
```

### Idempotency Key Pattern

```python
# Client sends unique key with every mutating request
POST /api/orchestration/start
Headers:
  Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000

# Server checks if key was seen before
async def start_workflow(
    request: StartWorkflowRequest,
    idempotency_key: Optional[str] = Header(None)
):
    if idempotency_key:
        # Check cache for previous result
        cached = await redis.get(f"idempotent:{idempotency_key}")
        if cached:
            # Return same response as before
            return StartWorkflowResponse(**json.loads(cached))
    
    # Process normally
    result = await orchestrator.start_workflow(...)
    
    if idempotency_key:
        # Cache result for 24 hours
        await redis.set(
            f"idempotent:{idempotency_key}",
            result.model_dump_json(),
            ex=86400
        )
    
    return result
```

This is especially important in this codebase for:
- `POST /orchestration/start` — don't start workflow twice
- `POST /orchestration/resume` — don't resume twice
- Document upload — don't create duplicate documents

**📂 See changelog as idempotency mechanism:**
- [`backend/app/orchestration/state.py` (L67-80)](../../backend/app/orchestration/state.py) — `StateChangelogEntry` records each commit, prevents duplicate operations

---

## 13. CORS & Security Headers {#security}

### CORS in This Codebase

```python
# backend/app/main.py (L93-100)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,    # ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production CORS — restrict methods and headers:**

```python
CORSMiddleware(
    allow_origins=["https://app.example.com"],  # Exact origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Not "*"
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    max_age=3600  # Cache preflight for 1 hour
)
```

### Security Headers Middleware

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"  # HTTPS only for 1 year
    )
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    # Remove framework fingerprint
    response.headers.pop("X-Powered-By", None)
    response.headers.pop("Server", None)
    
    return response
```

### Vite Proxy (This Codebase)

```js
// frontend/vite.config.js
proxy: {
    '/api/assistance': { target: 'http://localhost:8001' },  // Route first (more specific)
    '/api': { target: 'http://localhost:8000' },
    '/mcp': { target: 'http://localhost:8000' }
}
```

The frontend never makes cross-origin requests in development — Vite proxies all `/api` calls to the backend. This means no CORS issues during development.

**📂 See in codebase:**
- CORS setup: [`backend/app/main.py` (L93-100)](../../backend/app/main.py)
- Proxy config: [`frontend/vite.config.js`](../../frontend/vite.config.js)

---

## 14. API Contracts with Pydantic {#pydantic}

### Pydantic v2 Patterns Used in This Codebase

```python
# backend/app/models/schemas.py

# ✅ model_config with ConfigDict (Pydantic v2 syntax)
class HealthResponse(BaseModel):
    status: str = Field(default="healthy")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    })

# ✅ String Enum for validated choices
class ProviderType(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"

# ✅ Constrained fields
max_results: int = Field(default=100, ge=1, le=1000)  # 1-1000
name: str = Field(min_length=1, max_length=255)
freshness_days: Optional[int] = Field(default=None, ge=1)

# ✅ model_dump() not .dict() (Pydantic v2)
return profile.model_dump()
```

**Common Pydantic patterns for scalable APIs:**

```python
from pydantic import BaseModel, Field, field_validator, model_validator

class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list, max_length=10)
    
    # Validate individual fields
    @field_validator("name")
    @classmethod
    def name_must_be_slug(cls, v: str) -> str:
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError("Name must be lowercase alphanumeric with hyphens")
        return v
    
    # Cross-field validation
    @model_validator(mode='after')
    def check_name_not_reserved(self) -> 'CreateProjectRequest':
        reserved = {"admin", "api", "health", "metrics"}
        if self.name in reserved:
            raise ValueError(f"Name '{self.name}' is reserved")
        return self
```

**📂 See in codebase:**
- All schemas: [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py)
- Config model: [`backend/app/config.py`](../../backend/app/config.py)

---

## 15. Scalability Patterns {#scalability}

### Background Tasks (Don't Block the Response)

```python
# ❌ Blocks response until processing complete
@router.post("/upload")
async def upload_document(file: UploadFile):
    content = await file.read()
    parsed = await parse_file(content)       # Slow
    chunks = await chunk_document(parsed)    # Slow
    embeddings = await generate_embeddings() # Very slow (LLM call)
    await store_in_qdrant(embeddings)        # Slow
    return {"status": "done"}  # Client waited 30 seconds

# ✅ Return immediately, process in background
from fastapi import BackgroundTasks

@router.post("/upload")
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks
):
    doc_id = generate_id()
    content = await file.read()
    
    # Persist raw file first
    await save_raw_file(doc_id, content)
    
    # Schedule processing in background
    background_tasks.add_task(
        process_document_pipeline,
        doc_id=doc_id,
        content=content
    )
    
    # Return immediately (202 Accepted)
    return JSONResponse(
        status_code=202,
        content={"doc_id": doc_id, "status": "processing"}
    )

# Client polls for status
GET /api/documents/{doc_id}/status
→ {"status": "processing"} or {"status": "complete"}
```

### This codebase does this differently:

The `POST /orchestration/execute` returns quickly, and the actual multi-agent workflow runs asynchronously. Clients receive updates via SSE stream rather than polling.

### Dependency Injection (This Codebase Pattern)

```python
# backend/app/api/documents.py (L63-68)

async def get_qdrant_store() -> QdrantStore:
    """Dependency: returns initialized Qdrant store"""
    store = QdrantStore()
    await store.initialize()
    return store

# Inject into endpoint
@router.post("/upload")
async def upload_document(
    file: UploadFile,
    qdrant_store: QdrantStore = Depends(get_qdrant_store)
):
    ...
```

**Scalable pattern: cached singletons**

```python
_qdrant_store: Optional[QdrantStore] = None

async def get_qdrant_store() -> QdrantStore:
    """Return singleton — don't reconnect on every request"""
    global _qdrant_store
    if _qdrant_store is None:
        _qdrant_store = QdrantStore()
        await _qdrant_store.initialize()
    return _qdrant_store
```

### Router Organization (This Codebase Pattern)

```python
# backend/app/main.py (L103-106)

app.include_router(mcp_router)
app.include_router(orchestration_router)
app.include_router(documents_router)
app.include_router(projects_router)
```

Each router is a separate file with a single responsibility. This is the correct pattern for large APIs:

```
api/
├── __init__.py        ← re-exports routers
├── projects.py        ← /api/projects/*
├── documents.py       ← /api/documents/*
├── orchestration.py   ← /api/orchestration/*
├── mcp.py             ← /mcp/*
└── health.py          ← /health
```

**📂 See in codebase:**
- Router inclusion: [`backend/app/main.py` (L103-106)](../../backend/app/main.py)
- Router exports: [`backend/app/api/__init__.py`](../../backend/app/api/__init__.py)

### Liveness vs Readiness Health Checks

> **Interview question:** "What is the difference between `/health/live` and `/health/ready`?"

In Kubernetes (and any multi-replica deployment), there are **three distinct health signals**, each serving a different purpose:

| Endpoint | Kubernetes probe | Failing means | Action |
|----------|-----------------|---------------|--------|
| `GET /health/live` | Liveness | App is deadlocked / unresponsive | **Restart the pod** |
| `GET /health/ready` | Readiness | App is alive but not ready (warming up, overloaded) | **Stop routing traffic** — don't restart |
| `GET /health/startup` | Startup | App hasn't finished booting yet | **Wait longer** before liveness kicks in |

```python
# ✅ Production: split into three distinct endpoints

@app.get("/health/live")
async def liveness():
    """
    Ultra-fast check — only proves the process is not deadlocked.
    Should NEVER call external services (Redis, Qdrant, LLM providers).
    If this endpoint is slow or failing, k8s restarts the pod.
    """
    return {"status": "ok"}

@app.get("/health/ready")
async def readiness():
    """
    Deep check — proves the app can serve real traffic.
    Call all downstream dependencies. If any is down, return 503
    so the load balancer stops routing to this instance.
    """
    checks = {}
    try:
        await redis_client.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    try:
        await qdrant_store.client.get_collections()
        checks["qdrant"] = "ok"
    except Exception as e:
        checks["qdrant"] = f"error: {e}"

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={"status": "ready" if all_ok else "degraded", "checks": checks}
    )

@app.get("/health/startup")
async def startup():
    """
    Only used during initial startup phase.
    Allows slow initialisation (model loading, index warming) without
    triggering liveness restarts prematurely.
    """
    initialized = provider_factory is not None and state_manager is not None
    return JSONResponse(
        status_code=200 if initialized else 503,
        content={"initialized": initialized}
    )
```

**Common mistake:** A single `/health` endpoint that calls external services.
If Redis is slow, the liveness probe fails → Kubernetes restarts a healthy pod → cascading restart loop.
Always keep liveness **instant and I/O-free**.

```
# ❌ Anti-pattern: one /health endpoint that does deep checks
@app.get("/health")
async def health():
    await redis.ping()   # If Redis is slow → 503 → k8s restarts → stampede!
    return {"status": "ok"}

# ✅ Correct: separate liveness (no I/O) from readiness (deep check)
```

---

## 16. Testing APIs {#testing}

### Unit Test Pattern (This Codebase)

```python
# backend/tests/test_main.py

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_create_project_success():
    # Mock Qdrant dependency
    with patch("app.api.projects.get_qdrant_store") as mock_qdrant:
        mock_store = AsyncMock()
        mock_store.client.get_collections.return_value.collections = []
        mock_store.create_collection = AsyncMock()
        mock_qdrant.return_value = mock_store
        
        response = client.post("/api/projects/create", json={
            "name": "test-project",
            "description": "Test"
        })
        
        assert response.status_code == 200
        assert response.json()["project_id"] == "test-project"

def test_create_project_duplicate():
    with patch("app.api.projects.get_qdrant_store") as mock_qdrant:
        mock_store = AsyncMock()
        # Simulate existing collection
        from unittest.mock import MagicMock
        existing = MagicMock()
        existing.name = "project_test-project"
        mock_store.client.get_collections.return_value.collections = [existing]
        mock_qdrant.return_value = mock_store
        
        response = client.post("/api/projects/create", json={
            "name": "test-project"
        })
        
        assert response.status_code == 409  # Conflict
```

**📂 See in codebase:**
- Tests: [`backend/tests/`](../../backend/tests/)
- Test config: [`backend/tests/conftest.py`](../../backend/tests/conftest.py)

---

## 17. Interview Q&A {#interview-qa}

### Q1: "Design a REST API for a workflow automation system"

**Your answer structure:**

1. **Resources:**
   - `POST /workflows` → create workflow
   - `POST /workflows/{id}/execute` → trigger execution
   - `GET  /workflows/{id}` → get state
   - `GET  /workflows/{id}/stream` → SSE for real-time
   - `POST /workflows/{id}/resume` → resume from pause
   - `DELETE /workflows/{id}` → delete

2. **Status codes:**
   - 201 when workflow created
   - 202 when execution triggered (async)
   - 409 if workflow already running
   - 404 if workflow not found

3. **Real-time updates:** SSE over WebSocket (one-way, simpler)

4. **Idempotency:** `Idempotency-Key` header for execute/resume

5. **Versioning:** `/api/v1/workflows` for external clients

---

### Q2: "When would you use SSE vs WebSocket vs Polling?"

- **Polling:** legacy clients, simple use case, backend is simple
- **SSE:** one-way server-push (workflow updates, notifications), HTTP-friendly, auto-reconnect
- **WebSocket:** bidirectional (chat, collaboration, gaming), when latency < 50ms matters

**In this system:** SSE is correct — server pushes state changes, frontend never needs to send messages through the stream.

---

### Q3: "How do you version a public API without breaking clients?"

1. Add version prefix: `/api/v2/...`
2. Keep `/api` pointing to `/api/v1` (backward compat)
3. Deprecation period: announce v1 end-of-life 6+ months in advance
4. Response headers: `Deprecation: true`, `Sunset: 2025-01-01`
5. Never remove fields from responses (add only)
6. Never change field types (string → int breaks clients)

---

### Q4: "How would you rate-limit per user per endpoint?"

Redis sorted set sliding window:
- Key: `rate:{user_id}:{endpoint}`
- Add timestamp on every request: `ZADD key now now`
- Remove old: `ZREMRANGEBYSCORE key 0 (now - window)`
- Count: `ZCARD key`
- If count >= limit: return 429 with `Retry-After` header
- Response headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`

---

### Q5: "What's wrong with returning all data in a single API call?"

- Over-fetching: client gets 50 fields, uses 3
- Under-fetching: client needs related data, makes N+1 calls
- Performance: large payloads slow rendering
- Versioning: hard to change schema when one big response is shared

**Solutions:**
- Sparse fieldsets: `GET /projects?fields=id,name`
- GraphQL for complex, variable data requirements
- API composition layer (BFF - Backend for Frontend)

---

### Q6: "Design the error response schema for an enterprise API"

```json
{
    "error": {
        "code": "WORKFLOW_STATE_CONFLICT",
        "message": "Workflow is already running",
        "detail": "Project proj-123 has an active workflow at version 5",
        "timestamp": "2024-01-15T10:30:00Z",
        "request_id": "req_abc123",
        "documentation_url": "https://docs.example.com/errors/WORKFLOW_STATE_CONFLICT"
    }
}
```

- `code`: machine-readable, for client switch statements
- `message`: human-readable, for developers
- `detail`: context-specific, varies by instance
- `request_id`: for support tickets and log correlation
- `documentation_url`: self-service debugging

---

## Summary: API Design Checklist

### Design Phase
- [ ] Resources are nouns, URLs are consistent
- [ ] HTTP methods match semantics (GET=read, POST=create, etc.)
- [ ] Status codes are accurate (201 not 200 for create)
- [ ] Request/response models are separate Pydantic classes
- [ ] Error responses are consistent with machine-readable codes

### Implementation
- [ ] Input validated with Pydantic Field constraints
- [ ] File uploads validate type and size before reading
- [ ] Temp files cleaned up in `finally` blocks
- [ ] Long operations return 202 Accepted, not block
- [ ] SSE headers include `Cache-Control: no-cache`, `X-Accel-Buffering: no`

### Production Readiness
- [ ] Rate limiting on all mutating endpoints
- [ ] Idempotency keys supported on POST/PUT
- [ ] Versioning strategy documented
- [ ] Security headers added (HSTS, X-Frame-Options, etc.)
- [ ] CORS locked to known origins (not `*`)
- [ ] Error details hidden in production (`NODE_ENV != development`)
- [ ] All endpoints have integration tests
- [ ] JWT `audience` and `issuer` validated (not just signature)
- [ ] Separate `/health/live` and `/health/ready` endpoints
- [ ] Request correlation IDs (`X-Request-ID`) generated and logged

---

## ⚠️ POC vs Production: API Layer Gaps

| Concern | POC (this codebase) | Production add-on |
|---------|--------------------|--------------------|
| **JWT validation** | Signature only (`decode(token, key)`) | + `audience` and `issuer` claims validated |
| **Health checks** | Single `/health` | `/health/live` (no I/O), `/health/ready` (Redis + Qdrant ping) |
| **Request tracing** | No `X-Request-ID` | Middleware injects / preserves `X-Request-ID` on every request and response |
| **Structured logging** | Plain text | JSON logs carrying `request_id`, `project_id`, `user_id` on every line |
| **Error codes** | `HTTPException(detail=str(e))` | Structured `{"error": {"code": "...", "message": "...", "request_id": "..."}}` |
| **Connection pooling** | New Redis/Qdrant client per call | Single pooled client from lifespan, shared across all requests |
| **Graceful shutdown** | SIGTERM kills in-flight requests | `--timeout-graceful-shutdown 30` on uvicorn; lifespan drains before exit |
| **Rate limit granularity** | None | Per-user per-endpoint Redis sliding window with `X-RateLimit-*` headers |
| **CORS** | `allow_origins=["*"]` | Explicit origin allowlist from `settings.allowed_origins` |

**Sample interview answer:**
> "The current `/health` endpoint is a monolith — it calls Redis and Qdrant on every probe. In production that means a slow Redis response makes Kubernetes think the pod is unhealthy and restarts it, causing a cascade. I'd split it into `/health/live` which is instant and I/O-free, and `/health/ready` which does the full dependency check but is wired to the readiness probe, not the liveness probe. That way Kubernetes stops routing traffic to a degraded pod without restarting a healthy one."

---

**Made with Bob**
