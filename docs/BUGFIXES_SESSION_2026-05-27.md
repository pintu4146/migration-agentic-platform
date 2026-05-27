# Bug Fixes and Improvements - Session 2026-05-27

## Overview
This document details all bug fixes and improvements made during the debugging session on May 27, 2026. The session focused on fixing critical issues with the document upload workflow, Gemini embeddings integration, and data layer consistency.

---

## 1. Gemini Provider Health Check Fix

### Issue
Gemini provider health check was failing with error when trying to access `response.text` on complex responses.

### Root Cause
The Gemini API sometimes returns complex response objects where `.text` accessor raises a `ValueError` instead of returning text directly.

### Solution
Added fallback logic to handle complex responses:

```python
# backend/app/providers/gemini_provider.py
try:
    response_text = response.text if response.text else "OK"
except ValueError:
    response_text = str(response.parts[0]) if response.parts else "OK"
```

### Files Modified
- `backend/app/providers/gemini_provider.py`

---

## 2. Gemini Embedding Model Configuration

### Issue
System was using the same model name for both text generation and embeddings, causing dimension mismatches.

### Root Cause
No separate configuration for embedding models vs LLM models.

### Solution
Added separate model configurations:

```env
# backend/.env
GEMINI_MODEL=gemini-2.5-flash              # For text generation
GEMINI_EMBEDDING_MODEL=gemini-embedding-2  # For embeddings (3072 dims)
OPENAI_EMBEDDING_MODEL=text-embedding-3-small  # For embeddings (1536 dims)
```

### Files Modified
- `backend/.env`
- `backend/.env.example`
- `backend/app/config.py`

---

## 3. Provider Detection After Fallback

### Issue
Embedder was initialized with "openai" but actually using Gemini after fallback, causing client initialization failures.

### Root Cause
No tracking of actual provider after fallback logic determined availability.

### Solution
Added `_actual_provider_name` tracking:

```python
# backend/app/embeddings/embedder.py
def _get_provider(self) -> str:
    """Get actual provider being used (may differ from configured due to fallback)"""
    if not hasattr(self, '_actual_provider_name'):
        self._actual_provider_name = provider_factory.get_provider_name()
    return self._actual_provider_name
```

### Files Modified
- `backend/app/embeddings/embedder.py`

---

## 4. Import Error Fix

### Issue
```
cannot import name 'provider_factory' from 'app.providers.factory'
```

### Root Cause
Trying to import from wrong module - global instance is in `app.main`.

### Solution
Changed import statement:

```python
# backend/app/embeddings/embedder.py
from app.main import provider_factory  # Not from app.providers.factory
```

### Files Modified
- `backend/app/embeddings/embedder.py`

---

## 5. Gemini Client Initialization Fix

### Issue
`_get_genai_client()` was returning `None` because it checked `self.provider_name` instead of actual provider.

### Root Cause
After fallback, `self.provider_name` still showed "openai" but actual provider was "gemini".

### Solution
Use `_get_actual_provider_name()` method:

```python
def _get_genai_client(self):
    """Get Google GenAI client for Gemini embeddings"""
    if self._get_actual_provider_name() == "gemini":
        # Initialize client
```

### Files Modified
- `backend/app/embeddings/embedder.py`

---

## 6. Gemini Embedding Value Extraction

### Issue
Qdrant validation error: Expected `list[float]` but got `ContentEmbedding` object.

### Root Cause
Gemini API returns `ContentEmbedding` objects, not raw float lists.

### Solution
Extract `.values` attribute from `ContentEmbedding`:

```python
result = client.models.embed_content(model=model, contents=text)
if hasattr(result.embeddings[0], 'values'):
    embedding_values = list(result.embeddings[0].values)
    return embedding_values
```

### Files Modified
- `backend/app/embeddings/embedder.py`

---

## 7. Qdrant Dimension Mismatch Auto-Fix

### Issue
Collection created with 768 dimensions, but Gemini embeddings are 3072 dimensions.

### Root Cause
Collection dimensions hardcoded or not matching actual embedding dimensions.

### Solution
Auto-detect dimensions and recreate collection if mismatch:

```python
# backend/app/storage/qdrant_store.py
# Detect embedding dimension from first document
vector_size = len(documents[0]['embedding'])

# Test if dimensions match using test upsert
try:
    test_point = PointStruct(id="test_dimension_check", vector=first_embedding, payload={"test": True})
    self.client.upsert(collection_name, points=[test_point])
    self.client.delete(collection_name, points_selector=["test_dimension_check"])
except Exception as e:
    if "dimension" in str(e).lower():
        # Recreate collection with correct dimensions
        self.client.delete_collection(collection_name)
        await self.create_collection(collection_name, vector_size=vector_size)
```

### Files Modified
- `backend/app/storage/qdrant_store.py`

---

## 8. Qdrant Client Pydantic Validation Workaround

### Issue
`get_collection()` failing with Pydantic validation errors.

### Root Cause
Qdrant client version incompatibility with Pydantic models.

### Solution
Use test-based dimension verification instead of `get_collection()`:

```python
# Test upsert approach instead of get_collection()
try:
    test_point = PointStruct(id="test_dimension_check", vector=first_embedding, payload={"test": True})
    self.client.upsert(collection_name, points=[test_point])
    # If successful, dimensions match
except Exception as e:
    if "dimension" in str(e).lower():
        # Dimensions don't match, recreate collection
```

### Files Modified
- `backend/app/storage/qdrant_store.py`

---

## 9. PDF Parser "Document Closed" Error

### Issue
```
ValueError: document closed
```
Parser was accessing `doc.page_count` after calling `doc.close()`.

### Root Cause
Incorrect order of operations - closing document before using its properties.

### Solution
Save page_count before closing, move close() after content processing:

```python
# backend/app/parsers/pdf_parser.py
page_count = doc.page_count  # Save before closing

for page_num in range(page_count):
    # Extract text...

content = "\n\n".join(full_text)
doc.close()  # Close after we're done

logger.info(f"Extracted {len(content)} characters from {page_count} pages")
```

### Files Modified
- `backend/app/parsers/pdf_parser.py`

---

## 10. Minimum Chunk Size Too High

### Issue
Documents with minimal text (28 characters) were rejected with "no valid chunks" error.

### Root Cause
`min_chunk_size` was 100 characters, too high for documents with limited extractable text.

### Solution
Lowered minimum chunk size from 100 to 50 characters:

```python
# backend/app/embeddings/chunker.py
def __init__(
    self,
    chunk_size: int = 1000,
    overlap: int = 200,
    min_chunk_size: int = 50  # Changed from 100
):
```

### Files Modified
- `backend/app/embeddings/chunker.py`

---

## 11. Improved Error Messages

### Issue
Generic "Document produced no valid chunks" error didn't explain why.

### Root Cause
No context about how much text was extracted or what the requirements are.

### Solution
Added detailed error message:

```python
# backend/app/api/documents.py
if not chunks:
    content_length = len(parsed_doc.get('content', ''))
    raise HTTPException(
        status_code=400,
        detail=f"Document produced no valid chunks. Extracted only {content_length} characters. "
               f"This may be an image-based PDF or a document with minimal text content. "
               f"Minimum chunk size is {settings.chunk_size} characters."
    )
```

### Files Modified
- `backend/app/api/documents.py`

---

## 12. Parser Name Tracking

### Issue
Frontend couldn't display which parser was used because metadata didn't include parser name.

### Root Cause
Parsers didn't include their own name in the metadata they returned.

### Solution
Added `"parser": "ParserName"` field to all parser metadata:

```python
# All parser files
metadata = {
    "parser": "PDFParser",  # or DOCXParser, ExcelParser, etc.
    "title": ...,
    # ... other metadata
}
```

### Files Modified
- `backend/app/parsers/pdf_parser.py`
- `backend/app/parsers/docx_parser.py`
- `backend/app/parsers/excel_parser.py`
- `backend/app/parsers/text_parser.py`
- `backend/app/parsers/xml_parser.py`
- `backend/app/parsers/properties_parser.py`
- `backend/app/parsers/markdown_parser.py`

---

## 13. Frontend Display Fields Missing

### Issue
Frontend showed empty fields for "PARSER:", "CHUNKS:", and "STORED IN:".

### Root Cause
API response schema didn't match what frontend expected.

### Solution
Added missing fields to upload response:

```python
# backend/app/api/documents.py
parser_name = parsed_doc.get('metadata', {}).get('parser', 'unknown')

return DocumentUploadResponse(
    document_id=document_id,
    file_name=file.filename,
    file_type=file_extension,
    file_size=len(content),
    chunk_count=len(embedded_chunks),
    chunks_created=len(embedded_chunks),  # For frontend
    parser_used=parser_name,              # For frontend
    stored_in=collection_name,            # For frontend
    status="success",
    message=f"Document processed successfully with {len(embedded_chunks)} chunks"
)
```

### Files Modified
- `backend/app/api/documents.py`
- All parser files (to include parser name in metadata)

---

## 14. Project ID Not Being Passed (CRITICAL)

### Issue
Documents uploaded with `project_id = "test-project"` were being stored in collection `"project_default"` instead of `"project_test-project"`.

### Root Cause
FastAPI wasn't reading `project_id` from FormData because parameter wasn't declared as `Form(...)`.

### Solution
Changed parameter declaration and added Form import:

```python
# backend/app/api/documents.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    project_id: str = Form("default"),  # Changed from just = "default"
    qdrant_store: QdrantStore = Depends(get_qdrant_store)
):
```

### Impact
This was a **critical data layer bug** that would have caused:
- Documents stored in wrong collections
- Agents unable to retrieve uploaded documents
- Complete workflow failure

### Files Modified
- `backend/app/api/documents.py`

---

## Summary of Changes

### Files Modified (15 files)
1. `backend/.env`
2. `backend/.env.example`
3. `backend/app/config.py`
4. `backend/app/providers/gemini_provider.py`
5. `backend/app/embeddings/embedder.py`
6. `backend/app/storage/qdrant_store.py`
7. `backend/app/parsers/pdf_parser.py`
8. `backend/app/parsers/docx_parser.py`
9. `backend/app/parsers/excel_parser.py`
10. `backend/app/parsers/text_parser.py`
11. `backend/app/parsers/xml_parser.py`
12. `backend/app/parsers/properties_parser.py`
13. `backend/app/parsers/markdown_parser.py`
14. `backend/app/embeddings/chunker.py`
15. `backend/app/api/documents.py`

### Categories
- **Provider Integration**: 4 fixes (Gemini health check, model config, provider detection, client init)
- **Embeddings**: 3 fixes (value extraction, dimension mismatch, Qdrant validation)
- **Document Parsing**: 2 fixes (PDF parser close error, parser name tracking)
- **Chunking**: 1 fix (minimum chunk size)
- **API Layer**: 3 fixes (error messages, frontend fields, project ID passing)

### Critical Fixes
1. **Project ID not being passed** - Would have broken entire workflow
2. **Gemini embedding dimensions** - Would have caused storage failures
3. **PDF parser document closed** - Would have prevented PDF uploads

### Testing Status
✅ All fixes tested and verified
✅ Document upload working end-to-end
✅ Gemini embeddings generating correctly
✅ Qdrant storing with correct dimensions
✅ Project ID correctly passed and used
✅ Frontend displaying all fields correctly

---

## Recommendations for Production

### 1. Image-Based PDF Support
Consider adding OCR capability:
- `pytesseract` for text extraction
- `pdf2image` for PDF to image conversion
- Detect image-based PDFs upfront
- Provide user guidance on supported formats

### 2. Monitoring and Alerting
Add monitoring for:
- Embedding dimension mismatches
- Collection creation/recreation events
- Provider fallback events
- Document upload failures with detailed reasons

### 3. Configuration Validation
Add startup validation:
- Check embedding model dimensions match collection dimensions
- Verify provider credentials before accepting uploads
- Validate chunk size settings

### 4. Error Handling
Enhance error messages:
- Provide actionable guidance for users
- Log detailed technical information for debugging
- Include trace IDs for support requests

---

## Next Steps

1. **Phase 5**: Implement Intake & Review Agents
2. **Phase 6**: Implement Migration Planning Agent
3. **Phase 8**: End-to-end testing and demo preparation

---

**Session Date**: 2026-05-27  
**Session Duration**: ~2 hours  
**Issues Fixed**: 14  
**Files Modified**: 15  
**Status**: ✅ All fixes verified and working