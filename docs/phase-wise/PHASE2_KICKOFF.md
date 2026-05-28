# Phase 2: MCP Connector - Implementation Plan

## 🎯 Objective

Implement a configurable MCP (Model Context Protocol) connector module that provides plug-and-play knowledge retrieval from IBM Context Studio Gateway and other document sources.

## 📡 MCP Gateway Configuration

**IBM Context Studio MCP Gateway:**
- **Type:** streamable-http
- **URL:** `https://servicesessentials.ibm.com/mcp-gateway/service/gateway/servers/{server-id}/mcp`
- **Authentication:**
  - Bearer token (Authorization header)
  - API key (x-api-key header)
- **Configuration:** All settings configurable via environment variables

---

## 📋 Requirements from Task

### Core Requirements

1. **Configurable MCP Connector**
   - Base URL configuration
   - Bearer token authentication
   - Timeout and retry settings
   - Optional headers support
   - Source filters (space, page, attachment)
   - Retrieval profiles per agent

2. **Plug-and-Play Knowledge Retrieval**
   - Each agent can request different context slices
   - Retrieval driven by profiles/configs
   - Agents request context by intent, not mechanics
   - Shared MCP connector executes retrieval
   - Returns normalized JSON only

3. **Retrieval Profiles**
   - context_retrieval_profile
   - extraction_profile
   - questionnaire_profile
   - planning_profile
   - review_profile

4. **Profile Configuration**
   - Source types (page, attachment, etc.)
   - Content types (PDF, text, etc.)
   - Page filters (space, page IDs)
   - Attachment filters
   - Keyword filters
   - Section filters
   - Max results
   - Freshness hints

---

## 🏗️ Architecture Design

### Module Structure

```
backend/app/mcp/
├── __init__.py
├── connector.py           # Main MCP connector class
├── profiles.py            # Retrieval profile definitions
├── parsers.py             # Document parsers (PDF, DOCX, Excel)
├── normalizer.py          # Context normalization
└── cache.py               # Redis caching layer
```

### Key Components

#### 1. MCP Connector (`connector.py`)
- HTTP client for Confluence API
- Authentication handling
- Retry logic with exponential backoff
- Rate limiting
- Error handling

#### 2. Retrieval Profiles (`profiles.py`)
- Profile base class
- Predefined profiles for each agent
- Profile validation
- Profile serialization

#### 3. Document Parsers (`parsers.py`)
- PDF parser (PyMuPDF)
- DOCX parser (python-docx)
- Excel parser (pandas, openpyxl)
- Text extraction
- Metadata extraction

#### 4. Context Normalizer (`normalizer.py`)
- Normalize different source formats
- Extract metadata
- Preserve source IDs
- Evidence references
- Confidence scoring

#### 5. Cache Layer (`cache.py`)
- Redis integration
- Cache key generation
- TTL management
- Cache invalidation

---

## 📝 Implementation Tasks

### Task 1: MCP Connector Base
- [ ] Create `app/mcp/` directory structure
- [ ] Implement `MCPConnector` class
- [ ] Add Confluence API client
- [ ] Implement authentication
- [ ] Add retry logic
- [ ] Add rate limiting

### Task 2: Retrieval Profiles
- [ ] Create `RetrievalProfile` base class
- [ ] Define profile schema
- [ ] Implement predefined profiles
- [ ] Add profile validation
- [ ] Add profile serialization

### Task 3: Document Parsers
- [ ] Implement PDF parser
- [ ] Implement DOCX parser
- [ ] Implement Excel parser
- [ ] Add text extraction utilities
- [ ] Add metadata extraction

### Task 4: Context Normalization
- [ ] Create `ContextNormalizer` class
- [ ] Implement source format handlers
- [ ] Add metadata extraction
- [ ] Preserve evidence references
- [ ] Add confidence scoring

### Task 5: Caching Layer
- [ ] Implement Redis cache wrapper
- [ ] Add cache key generation
- [ ] Implement TTL management
- [ ] Add cache invalidation logic

### Task 6: API Integration
- [ ] Add MCP endpoints to FastAPI
- [ ] Create request/response models
- [ ] Add retrieval endpoint
- [ ] Add profile management endpoints
- [ ] Add cache management endpoints

### Task 7: Testing
- [ ] Unit tests for connector
- [ ] Unit tests for parsers
- [ ] Unit tests for normalizer
- [ ] Integration tests
- [ ] Mock Confluence API responses

### Task 8: Documentation
- [ ] Update README with MCP usage
- [ ] Add API documentation
- [ ] Create profile examples
- [ ] Add troubleshooting guide

---

## 🔌 API Design

### Endpoints

```python
# Retrieve context using profile
POST /mcp/retrieve
{
  "project_id": "proj_123",
  "profile": {
    "profile_name": "extraction_profile",
    "source_types": ["page", "attachment"],
    "max_results": 50
  }
}

# Get available profiles
GET /mcp/profiles

# Create custom profile
POST /mcp/profiles
{
  "name": "custom_profile",
  "source_types": ["page"],
  "filters": {...}
}

# Clear cache
DELETE /mcp/cache/{project_id}
```

---

## 📊 Data Models

### Retrieval Profile
```python
class RetrievalProfile(BaseModel):
    profile_name: str
    source_types: Optional[List[str]] = None
    content_types: Optional[List[str]] = None
    page_filters: Optional[Dict[str, Any]] = None
    attachment_filters: Optional[Dict[str, Any]] = None
    keyword_filters: Optional[List[str]] = None
    section_filters: Optional[List[str]] = None
    max_results: int = 100
    freshness_days: Optional[int] = None
```

### Context Pack
```python
class ContextPack(BaseModel):
    project_id: str
    profile_name: str
    documents: List[Document]
    total_count: int
    retrieved_at: datetime
    cache_key: str
```

### Document
```python
class Document(BaseModel):
    id: str
    source: str  # confluence, upload, etc.
    type: str    # page, attachment, etc.
    title: str
    content: str
    metadata: Dict[str, Any]
    evidence_refs: List[str]
    confidence: float
```

---

## 🧪 Testing Strategy

### Unit Tests
- MCP connector methods
- Profile validation
- Parser functions
- Normalizer logic
- Cache operations

### Integration Tests
- End-to-end retrieval flow
- Profile-based filtering
- Cache hit/miss scenarios
- Error handling

### Mock Data
- Sample Confluence responses
- Sample documents (PDF, DOCX, Excel)
- Sample profiles

---

## 📦 Dependencies

Already in requirements.txt:
- ✅ httpx (HTTP client)
- ✅ aiohttp (async HTTP)
- ✅ PyMuPDF (PDF parsing)
- ✅ python-docx (DOCX parsing)
- ✅ pandas (Excel parsing)
- ✅ openpyxl (Excel parsing)
- ✅ redis (caching)
- ✅ tenacity (retry logic)

---

## 🎯 Success Criteria

Phase 2 is successful if:
- [ ] MCP connector can retrieve from Confluence
- [ ] Retrieval profiles work as expected
- [ ] Documents are parsed correctly
- [ ] Context is normalized properly
- [ ] Caching reduces API calls
- [ ] API endpoints are functional
- [ ] Tests pass
- [ ] Documentation is complete

---

## 🚀 Next Steps After Phase 2

**Phase 3: LangGraph Orchestration**
- Implement LangGraph workflow
- Add shared state management
- Implement transaction-style state commits
- Add node transitions and checkpointing

---

## 📝 Notes

- Keep MCP connector generic enough to support other sources later
- Profile system should be extensible
- Cache strategy should be configurable
- Error handling should be robust
- Logging should be comprehensive

---

**Status:** Ready to begin Phase 2 implementation
**Estimated Time:** 4-6 hours
**Priority:** High