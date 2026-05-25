# Phase 4: Multi-Source Knowledge Ingestion Enhancement

**Status:** Implementation Complete (Type errors pending)  
**Date:** 2026-05-25  
**Objective:** Implement resilient multi-source knowledge ingestion with MCP fallback strategy

---

## Overview

Enhanced the Context Retrieval Agent with a robust multi-source fallback strategy to handle MCP failures gracefully. The system now supports three knowledge sources with automatic fallback:

1. **MCP (IBM Context Studio)** - Primary source
2. **Uploaded Documents** - Secondary source via Qdrant
3. **Cached Context** - Tertiary source from previous runs

---

## Implementation Summary

### 1. Document Parsers Module

Created `backend/app/parsers/` with support for multiple file formats:

#### Files Created:
- `__init__.py` (20 lines) - Module exports
- `pdf_parser.py` (139 lines) - PDF extraction using PyMuPDF
- `docx_parser.py` (118 lines) - Word document parsing
- `excel_parser.py` (123 lines) - Excel spreadsheet parsing
- `text_parser.py` (103 lines) - Plain text/markdown parsing
- `parser_factory.py` (128 lines) - Automatic parser selection

**Total:** 631 lines

#### Supported Formats:
- PDF (`.pdf`)
- Word (`.docx`, `.doc`)
- Excel (`.xlsx`, `.xls`)
- Text (`.txt`, `.md`, `.markdown`, `.rst`, `.log`)

#### Key Features:
- Automatic parser selection by file extension
- Metadata extraction (author, dates, page count)
- Table extraction from Word/Excel
- Multi-encoding support for text files (UTF-8, UTF-16, Latin-1)
- Error handling with fallback encodings

---

### 2. Embeddings Module

Created `backend/app/embeddings/` for document chunking and embedding generation:

#### Files Created:
- `__init__.py` (17 lines) - Module exports
- `chunker.py` (227 lines) - Smart text chunking
- `embedder.py` (241 lines) - Gemini/OpenAI embeddings

**Total:** 485 lines

#### Chunking Features:
- **Chunk Size:** 1000 characters (configurable)
- **Overlap:** 200 characters (20%)
- **Sentence Boundary Detection:** Splits on `.!?` with whitespace
- **Word Boundary Fallback:** For non-sentence text
- **Minimum Chunk Size:** 100 characters to avoid fragments
- **Metadata Preservation:** Attaches source metadata to each chunk

#### Embedding Features:
- **Gemini Support:** `models/embedding-001` with task types
  - `retrieval_document` for document embedding
  - `retrieval_query` for query embedding
- **OpenAI Support:** `text-embedding-3-small`
- **Batch Processing:** Configurable batch size (default: 10)
- **Async Generation:** Parallel embedding generation
- **Provider Abstraction:** Same interface for both providers

---

### 3. Document Upload API

Created `backend/app/api/documents.py` (281 lines) with endpoints:

#### Endpoints:

**POST /api/documents/upload**
- Upload and process documents
- Parse → Chunk → Embed → Store in Qdrant
- Returns document metadata and chunk count

**POST /api/documents/search**
- Semantic search using query embeddings
- Filters by project and metadata
- Returns ranked results with scores

**GET /api/documents/list**
- List all documents in a project
- Returns document metadata

**DELETE /api/documents/{document_id}**
- Delete document and all chunks
- Returns deletion count

#### Processing Pipeline:
```
Upload → Validate → Parse → Chunk → Embed → Store → Return Metadata
```

---

### 4. Enhanced Context Retrieval Agent

Updated `backend/app/agents/context_retrieval_agent.py` with multi-source fallback:

#### Multi-Source Strategy:

```python
async def execute(state):
    # Try Source 1: MCP (IBM Context Studio)
    context_pack = await _try_mcp_retrieval(project_id, state)
    
    # Try Source 2: Uploaded Documents (if MCP failed)
    if context_pack is None:
        context_pack = await _try_uploaded_documents(project_id, state)
    
    # Try Source 3: Cached Context (if both failed)
    if context_pack is None:
        context_pack = await _try_cached_context(project_id, state)
    
    # Return error only if all sources failed
    if context_pack is None:
        return error_response("All sources failed")
    
    return success_response(context_pack)
```

#### New Methods:
- `_try_mcp_retrieval()` - Attempt MCP retrieval
- `_try_uploaded_documents()` - Query Qdrant for uploaded docs
- `_try_cached_context()` - Use cached context from state
- `_documents_to_context_pack()` - Convert Qdrant docs to ContextPack
- `_dict_to_context_pack()` - Reconstruct ContextPack from dict
- `_error_response()` - Standardized error response

#### Tracing Enhancement:
```python
"trace_metadata": {
    "context_retrieval": {
        "documents_retrieved": 15,
        "source_used": "uploaded_documents",
        "sources_tried": ["mcp (error)", "uploaded_documents"],
        "timestamp": "2026-05-25T18:30:00Z"
    }
}
```

---

### 5. Configuration Updates

Updated `backend/app/config.py` with new settings:

```python
# Document Processing
chunk_size: int = 1000
chunk_overlap: int = 200
max_file_size_mb: int = 50

# Provider Selection
@property
def default_provider(self) -> str:
    """Get default provider based on configuration."""
    if self.openai_api_key:
        return self.primary_provider
    elif self.gemini_api_key:
        return "gemini"
    else:
        raise ValueError("No LLM provider configured")
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   Context Retrieval Agent                    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Multi-Source Fallback Strategy                    │    │
│  │                                                     │    │
│  │  1. Try MCP (IBM Context Studio)                   │    │
│  │     ├─ Success → Return ContextPack                │    │
│  │     └─ Failure → Try Next Source                   │    │
│  │                                                     │    │
│  │  2. Try Uploaded Documents (Qdrant)                │    │
│  │     ├─ Query by project_id                         │    │
│  │     ├─ Convert to ContextPack format               │    │
│  │     ├─ Success → Return ContextPack                │    │
│  │     └─ Failure → Try Next Source                   │    │
│  │                                                     │    │
│  │  3. Try Cached Context (State)                     │    │
│  │     ├─ Check state.context_pack                    │    │
│  │     ├─ Reconstruct ContextPack                     │    │
│  │     ├─ Success → Return ContextPack                │    │
│  │     └─ Failure → Return Error                      │    │
│  │                                                     │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                  Document Upload Pipeline                    │
│                                                              │
│  Upload File                                                 │
│      ↓                                                       │
│  Validate Format (PDF, DOCX, XLSX, TXT, MD)                │
│      ↓                                                       │
│  Parse Document (ParserFactory)                             │
│      ├─ PDFParser (PyMuPDF)                                 │
│      ├─ DOCXParser (python-docx)                            │
│      ├─ ExcelParser (pandas/openpyxl)                       │
│      └─ TextParser (multi-encoding)                         │
│      ↓                                                       │
│  Chunk Content (DocumentChunker)                            │
│      ├─ Sentence boundary detection                         │
│      ├─ 1000 char chunks with 200 char overlap             │
│      └─ Metadata preservation                               │
│      ↓                                                       │
│  Generate Embeddings (EmbeddingGenerator)                   │
│      ├─ Gemini: models/embedding-001                        │
│      └─ OpenAI: text-embedding-3-small                      │
│      ↓                                                       │
│  Store in Qdrant (QdrantStore)                              │
│      ├─ Collection: project_{project_id}                    │
│      ├─ Vector + Metadata                                   │
│      └─ Searchable by semantic similarity                   │
│      ↓                                                       │
│  Return Metadata                                             │
│      ├─ document_id                                         │
│      ├─ chunk_count                                         │
│      └─ status                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## File Structure

```
backend/
├── app/
│   ├── parsers/                    # NEW: Document parsing
│   │   ├── __init__.py            (20 lines)
│   │   ├── pdf_parser.py          (139 lines)
│   │   ├── docx_parser.py         (118 lines)
│   │   ├── excel_parser.py        (123 lines)
│   │   ├── text_parser.py         (103 lines)
│   │   └── parser_factory.py      (128 lines)
│   │
│   ├── embeddings/                 # NEW: Chunking & embeddings
│   │   ├── __init__.py            (17 lines)
│   │   ├── chunker.py             (227 lines)
│   │   └── embedder.py            (241 lines)
│   │
│   ├── api/
│   │   ├── documents.py           # NEW: Upload API (281 lines)
│   │   └── ...
│   │
│   ├── agents/
│   │   ├── context_retrieval_agent.py  # ENHANCED (450+ lines)
│   │   └── ...
│   │
│   └── config.py                   # UPDATED: Added chunking settings
│
└── requirements.txt                # Already has all dependencies
```

**Total New Code:** ~1,400 lines

---

## Dependencies

All required dependencies already in `requirements.txt`:

```txt
# Document Parsing
PyMuPDF==1.23.8          # PDF parsing
python-docx==1.1.0       # Word documents
pandas==2.1.4            # Excel parsing
openpyxl==3.1.2          # Excel support

# LLM & Embeddings
openai==1.10.0           # OpenAI embeddings
google-generativeai==0.3.2  # Gemini embeddings

# Vector Store
qdrant-client==1.7.0     # Vector storage
```

---

## Usage Examples

### 1. Upload Document

```python
# Upload a PDF
files = {'file': open('architecture.pdf', 'rb')}
response = requests.post(
    'http://localhost:8000/api/documents/upload',
    files=files,
    params={'project_id': 'proj_001'}
)

# Response:
{
    "document_id": "proj_001_architecture.pdf_1234567890",
    "file_name": "architecture.pdf",
    "file_type": ".pdf",
    "file_size": 524288,
    "chunk_count": 42,
    "status": "success",
    "message": "Document processed successfully with 42 chunks"
}
```

### 2. Search Documents

```python
# Semantic search
response = requests.post(
    'http://localhost:8000/api/documents/search',
    json={
        "query": "What is the authentication mechanism?",
        "limit": 5,
        "filters": {"source_type": "pdf"}
    },
    params={'project_id': 'proj_001'}
)

# Response:
{
    "results": [
        {
            "text": "The system uses OAuth 2.0 for authentication...",
            "score": 0.89,
            "metadata": {
                "source_file": "architecture.pdf",
                "page": 15
            }
        },
        ...
    ],
    "total": 5
}
```

### 3. Context Retrieval with Fallback

```python
# Agent execution
state = {
    "project_id": "proj_001",
    "state_version": 1
}

# Agent tries sources in order:
# 1. MCP → Failed (connection timeout)
# 2. Uploaded Documents → Success (found 15 docs)
# 3. Cache → Not tried (already succeeded)

result = await context_retrieval_agent.execute(state)

# Result:
{
    "context_pack": {...},
    "normalized_docs": [15 documents],
    "phase": "extraction",
    "trace_metadata": {
        "context_retrieval": {
            "documents_retrieved": 15,
            "source_used": "uploaded_documents",
            "sources_tried": ["mcp (error: timeout)", "uploaded_documents"]
        }
    }
}
```

---

## Pending Tasks

### 1. Fix Type Errors

**Location:** `backend/app/agents/context_retrieval_agent.py`

**Issues:**
- Missing `QdrantStore` implementation
- `DocumentType.DOCUMENT` enum value doesn't exist
- `DocumentMetadata` missing required `source_id` parameter

**Resolution:**
1. Create `backend/app/storage/qdrant_store.py`
2. Update `DocumentType` enum in `backend/app/mcp/models.py`
3. Update `DocumentMetadata` model to make `source_id` optional

### 2. Create Qdrant Store Implementation

**File:** `backend/app/storage/qdrant_store.py`

**Required Methods:**
- `initialize()` - Setup Qdrant client and collections
- `add_documents()` - Store embedded chunks
- `search()` - Semantic search with filters
- `list_documents()` - Get all documents in collection
- `delete_document()` - Remove document and chunks

### 3. Integration Testing

**Test Files Needed:**
- `backend/tests/test_parsers.py` - Parser unit tests
- `backend/tests/test_chunker.py` - Chunking tests
- `backend/tests/test_embedder.py` - Embedding tests
- `backend/tests/test_document_api.py` - API integration tests
- `backend/tests/test_context_retrieval_fallback.py` - Fallback logic tests

---

## Benefits

### 1. Resilience
- System continues working even if MCP is down
- Multiple fallback options ensure availability
- Graceful degradation with clear error messages

### 2. Flexibility
- Support for multiple document formats
- Plug-and-play parser architecture
- Provider-agnostic embeddings

### 3. Observability
- Detailed tracing of source attempts
- Clear indication of which source was used
- Error tracking for each source

### 4. Performance
- Async processing throughout
- Batch embedding generation
- Efficient chunking with overlap

### 5. User Experience
- Upload documents directly through UI
- Semantic search across all sources
- Transparent fallback behavior

---

## Next Steps

1. **Fix Type Errors** - Resolve import and type issues
2. **Implement QdrantStore** - Complete vector storage layer
3. **Integration Testing** - Test full upload → search → retrieval flow
4. **UI Integration** - Add document upload to frontend
5. **Documentation** - Update API docs with new endpoints

---

## Success Criteria

✅ **Completed:**
- Document parsers for 4+ formats
- Smart chunking with sentence boundaries
- Gemini/OpenAI embedding support
- Document upload API
- Multi-source fallback logic
- Configuration updates

⏳ **Pending:**
- Type error resolution
- QdrantStore implementation
- Integration tests
- UI integration

---

## Made with Bob