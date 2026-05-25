# Phase 2: MCP Connector & Context Ingestion Module

## Overview

Phase 2 implements the configurable MCP (Model Context Protocol) connector module that enables plug-and-play knowledge retrieval from Confluence Cloud and other document sources. This phase establishes the foundation for context-aware agent operations.

## Objectives

1. **Implement MCP Connector Module**
   - Configurable connection to Confluence Cloud
   - Support for multiple retrieval profiles
   - Normalized JSON output
   - Error handling and retry logic

2. **Build Document Parsing Pipeline**
   - PDF parsing (PyMuPDF)
   - DOCX parsing (python-docx)
   - Excel parsing (pandas, openpyxl)
   - Text extraction and normalization

3. **Implement Vector Store**
   - In-memory Qdrant for POC
   - Embedding generation
   - Semantic search capability
   - Context retrieval optimization

4. **Create Context Normalization Layer**
   - Unified document format
   - Source tracking and evidence preservation
   - Metadata extraction
   - Content chunking for LLM consumption

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Connector Module                      │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Retrieval Profile Manager                     │ │
│  │  - context_retrieval_profile                           │ │
│  │  - extraction_profile                                  │ │
│  │  - questionnaire_profile                               │ │
│  │  - planning_profile                                    │ │
│  └────────────────┬───────────────────────────────────────┘ │
│                   │                                          │
│  ┌────────────────▼───────────────────────────────────────┐ │
│  │           Confluence Cloud Client                       │ │
│  │  - Authentication (Bearer Token)                       │ │
│  │  - Space/Page Filtering                                │ │
│  │  - Attachment Retrieval                                │ │
│  │  - Rate Limiting & Retry                               │ │
│  └────────────────┬───────────────────────────────────────┘ │
│                   │                                          │
└───────────────────┼──────────────────────────────────────────┘
                    │
    ┌───────────────▼───────────────┐
    │   Document Parser Pipeline    │
    │                                │
    │  ┌──────────┐  ┌──────────┐  │
    │  │   PDF    │  │  DOCX    │  │
    │  │  Parser  │  │  Parser  │  │
    │  └──────────┘  └──────────┘  │
    │                                │
    │  ┌──────────┐  ┌──────────┐  │
    │  │  Excel   │  │   Text   │  │
    │  │  Parser  │  │  Parser  │  │
    │  └──────────┘  └──────────┘  │
    └───────────────┬────────────────┘
                    │
    ┌───────────────▼────────────────┐
    │   Context Normalization        │
    │                                 │
    │  - Unified Document Format      │
    │  - Source ID Assignment         │
    │  - Metadata Extraction          │
    │  - Content Chunking             │
    └───────────────┬─────────────────┘
                    │
    ┌───────────────▼─────────────────┐
    │   Qdrant Vector Store           │
    │                                  │
    │  - Embedding Generation          │
    │  - Semantic Search               │
    │  - Context Retrieval             │
    └──────────────────────────────────┘
```

## Implementation

### 1. MCP Connector Configuration

```python
# backend/app/mcp/config.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any

class MCPConfig(BaseModel):
    """MCP Connector Configuration"""
    
    # Connection Settings
    base_url: str = Field(..., description="Confluence Cloud base URL")
    bearer_token: str = Field(..., description="API authentication token")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    
    # Optional Headers
    custom_headers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Additional HTTP headers"
    )
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(
        default=60,
        description="Maximum requests per minute"
    )
    
    class Config:
        env_prefix = "MCP_"

class RetrievalProfile(BaseModel):
    """Configurable retrieval profile for different agent needs"""
    
    profile_name: str
    source_types: List[str] = Field(
        default=["page", "attachment"],
        description="Types of sources to retrieve"
    )
    content_types: List[str] = Field(
        default=["text/html", "application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
        description="MIME types to include"
    )
    
    # Filters
    space_keys: Optional[List[str]] = Field(
        default=None,
        description="Confluence space keys to search"
    )
    page_ids: Optional[List[str]] = Field(
        default=None,
        description="Specific page IDs to retrieve"
    )
    labels: Optional[List[str]] = Field(
        default=None,
        description="Page labels to filter by"
    )
    keyword_filters: Optional[List[str]] = Field(
        default=None,
        description="Keywords to search for"
    )
    
    # Retrieval Settings
    max_results: int = Field(
        default=50,
        description="Maximum number of results to return"
    )
    include_attachments: bool = Field(
        default=True,
        description="Whether to include attachments"
    )
    freshness_days: Optional[int] = Field(
        default=None,
        description="Only retrieve content modified within N days"
    )
    
    # Chunking Settings
    chunk_size: int = Field(
        default=1000,
        description="Characters per chunk for LLM consumption"
    )
    chunk_overlap: int = Field(
        default=200,
        description="Overlap between chunks"
    )

# Predefined Profiles
CONTEXT_RETRIEVAL_PROFILE = RetrievalProfile(
    profile_name="context_retrieval",
    source_types=["page", "attachment"],
    max_results=100,
    include_attachments=True,
    chunk_size=1500,
    chunk_overlap=300
)

EXTRACTION_PROFILE = RetrievalProfile(
    profile_name="extraction",
    source_types=["page"],
    content_types=["text/html"],
    max_results=50,
    include_attachments=False,
    chunk_size=2000,
    chunk_overlap=400
)

QUESTIONNAIRE_PROFILE = RetrievalProfile(
    profile_name="questionnaire",
    source_types=["page"],
    max_results=30,
    include_attachments=False,
    chunk_size=1000,
    chunk_overlap=200
)

PLANNING_PROFILE = RetrievalProfile(
    profile_name="planning",
    source_types=["page", "attachment"],
    labels=["architecture", "deployment", "infrastructure"],
    max_results=50,
    include_attachments=True,
    chunk_size=2000,
    chunk_overlap=400
)
```

### 2. MCP Connector Implementation

```python
# backend/app/mcp/connector.py
import httpx
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import MCPConfig, RetrievalProfile

logger = logging.getLogger(__name__)

class MCPConnectorError(Exception):
    """Base exception for MCP connector errors"""
    pass

class MCPConnector:
    """
    Configurable MCP connector for Confluence Cloud.
    
    Features:
    - Plug-and-play configuration
    - Multiple retrieval profiles
    - Automatic retry with exponential backoff
    - Rate limiting
    - Normalized JSON output
    """
    
    def __init__(self, config: MCPConfig):
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.base_url,
            headers={
                "Authorization": f"Bearer {config.bearer_token}",
                "Accept": "application/json",
                **(config.custom_headers or {})
            },
            timeout=config.timeout
        )
        self._rate_limiter = asyncio.Semaphore(config.rate_limit_per_minute)
        self._last_request_time = datetime.now()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make rate-limited HTTP request with retry"""
        
        async with self._rate_limiter:
            # Rate limiting: ensure minimum time between requests
            now = datetime.now()
            time_since_last = (now - self._last_request_time).total_seconds()
            min_interval = 60.0 / self.config.rate_limit_per_minute
            
            if time_since_last < min_interval:
                await asyncio.sleep(min_interval - time_since_last)
            
            self._last_request_time = datetime.now()
            
            try:
                response = await self.client.request(method, endpoint, **kwargs)
                response.raise_for_status()
                return response.json()
            
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
                raise MCPConnectorError(f"HTTP {e.response.status_code}: {e.response.text}")
            
            except httpx.RequestError as e:
                logger.error(f"Request error: {str(e)}")
                raise MCPConnectorError(f"Request failed: {str(e)}")
    
    async def retrieve_context(
        self,
        profile: RetrievalProfile
    ) -> Dict[str, Any]:
        """
        Retrieve context using specified profile.
        
        Args:
            profile: Retrieval profile configuration
            
        Returns:
            Normalized context pack with documents and metadata
        """
        
        logger.info(f"Retrieving context with profile: {profile.profile_name}")
        
        # Build CQL query
        cql_query = self._build_cql_query(profile)
        
        # Search Confluence
        search_results = await self._search_confluence(cql_query, profile.max_results)
        
        # Retrieve page content
        pages = await self._retrieve_pages(search_results, profile)
        
        # Retrieve attachments if needed
        attachments = []
        if profile.include_attachments:
            attachments = await self._retrieve_attachments(search_results, profile)
        
        # Normalize results
        context_pack = self._normalize_context(pages, attachments, profile)
        
        logger.info(
            f"Retrieved {len(pages)} pages and {len(attachments)} attachments"
        )
        
        return context_pack
    
    def _build_cql_query(self, profile: RetrievalProfile) -> str:
        """Build Confluence Query Language (CQL) query from profile"""
        
        conditions = []
        
        # Source types
        if "page" in profile.source_types:
            conditions.append("type=page")
        
        # Space filters
        if profile.space_keys:
            space_condition = " OR ".join([f"space={key}" for key in profile.space_keys])
            conditions.append(f"({space_condition})")
        
        # Label filters
        if profile.labels:
            label_condition = " AND ".join([f"label={label}" for label in profile.labels])
            conditions.append(f"({label_condition})")
        
        # Keyword filters
        if profile.keyword_filters:
            keyword_condition = " OR ".join([f"text~\"{kw}\"" for kw in profile.keyword_filters])
            conditions.append(f"({keyword_condition})")
        
        # Freshness filter
        if profile.freshness_days:
            cutoff_date = (datetime.now() - timedelta(days=profile.freshness_days)).strftime("%Y-%m-%d")
            conditions.append(f"lastModified >= {cutoff_date}")
        
        # Combine conditions
        cql = " AND ".join(conditions) if conditions else "type=page"
        
        logger.debug(f"Built CQL query: {cql}")
        return cql
    
    async def _search_confluence(
        self,
        cql: str,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """Search Confluence using CQL"""
        
        results = []
        start = 0
        limit = min(50, max_results)  # Confluence API limit per request
        
        while len(results) < max_results:
            response = await self._make_request(
                "GET",
                "/wiki/rest/api/content/search",
                params={
                    "cql": cql,
                    "start": start,
                    "limit": limit,
                    "expand": "body.storage,version,space,metadata.labels"
                }
            )
            
            batch = response.get("results", [])
            if not batch:
                break
            
            results.extend(batch)
            start += limit
            
            if len(batch) < limit:
                break
        
        return results[:max_results]
    
    async def _retrieve_pages(
        self,
        search_results: List[Dict[str, Any]],
        profile: RetrievalProfile
    ) -> List[Dict[str, Any]]:
        """Retrieve full page content"""
        
        pages = []
        
        for result in search_results:
            if result.get("type") != "page":
                continue
            
            page = {
                "id": result["id"],
                "title": result["title"],
                "space_key": result["space"]["key"],
                "space_name": result["space"]["name"],
                "version": result["version"]["number"],
                "last_modified": result["version"]["when"],
                "content": result["body"]["storage"]["value"],
                "labels": [label["name"] for label in result.get("metadata", {}).get("labels", {}).get("results", [])],
                "url": f"{self.config.base_url}/wiki{result['_links']['webui']}"
            }
            
            pages.append(page)
        
        return pages
    
    async def _retrieve_attachments(
        self,
        search_results: List[Dict[str, Any]],
        profile: RetrievalProfile
    ) -> List[Dict[str, Any]]:
        """Retrieve attachments from pages"""
        
        attachments = []
        
        for result in search_results:
            page_id = result["id"]
            
            # Get attachments for this page
            response = await self._make_request(
                "GET",
                f"/wiki/rest/api/content/{page_id}/child/attachment",
                params={"expand": "version"}
            )
            
            for attachment in response.get("results", []):
                # Filter by content type
                media_type = attachment.get("metadata", {}).get("mediaType", "")
                if profile.content_types and media_type not in profile.content_types:
                    continue
                
                # Download attachment content
                download_url = attachment["_links"]["download"]
                content_response = await self.client.get(download_url)
                
                attachments.append({
                    "id": attachment["id"],
                    "title": attachment["title"],
                    "media_type": media_type,
                    "size": attachment["extensions"]["fileSize"],
                    "page_id": page_id,
                    "version": attachment["version"]["number"],
                    "last_modified": attachment["version"]["when"],
                    "content": content_response.content,
                    "url": f"{self.config.base_url}{download_url}"
                })
        
        return attachments
    
    def _normalize_context(
        self,
        pages: List[Dict[str, Any]],
        attachments: List[Dict[str, Any]],
        profile: RetrievalProfile
    ) -> Dict[str, Any]:
        """Normalize retrieved content into context pack"""
        
        return {
            "profile_name": profile.profile_name,
            "retrieved_at": datetime.utcnow().isoformat(),
            "total_pages": len(pages),
            "total_attachments": len(attachments),
            "pages": pages,
            "attachments": attachments,
            "metadata": {
                "source": "confluence_cloud",
                "base_url": self.config.base_url,
                "retrieval_settings": {
                    "max_results": profile.max_results,
                    "include_attachments": profile.include_attachments,
                    "chunk_size": profile.chunk_size,
                    "chunk_overlap": profile.chunk_overlap
                }
            }
        }
```

### 3. Document Parser Pipeline

```python
# backend/app/mcp/parsers.py
import io
from typing import Dict, Any, List
import logging
from abc import ABC, abstractmethod

import pymupdf  # PyMuPDF
from docx import Document
import pandas as pd
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class DocumentParser(ABC):
    """Base class for document parsers"""
    
    @abstractmethod
    def parse(self, content: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Parse document content"""
        pass

class PDFParser(DocumentParser):
    """Parse PDF documents using PyMuPDF"""
    
    def parse(self, content: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract text from PDF"""
        
        try:
            doc = pymupdf.open(stream=content, filetype="pdf")
            
            text_content = []
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                text_content.append({
                    "page": page_num,
                    "text": text
                })
            
            doc.close()
            
            return {
                "source_id": metadata.get("id"),
                "source_type": "pdf",
                "title": metadata.get("title"),
                "total_pages": len(text_content),
                "content": text_content,
                "full_text": "\n\n".join([p["text"] for p in text_content]),
                "metadata": metadata
            }
        
        except Exception as e:
            logger.error(f"PDF parsing error: {str(e)}")
            return {
                "source_id": metadata.get("id"),
                "source_type": "pdf",
                "error": str(e),
                "metadata": metadata
            }

class DOCXParser(DocumentParser):
    """Parse DOCX documents using python-docx"""
    
    def parse(self, content: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract text from DOCX"""
        
        try:
            doc = Document(io.BytesIO(content))
            
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)
            
            tables = []
            for table in doc.tables:
                table_data = []
                for row in table.rows:
                    row_data = [cell.text for cell in row.cells]
                    table_data.append(row_data)
                tables.append(table_data)
            
            return {
                "source_id": metadata.get("id"),
                "source_type": "docx",
                "title": metadata.get("title"),
                "paragraphs": paragraphs,
                "tables": tables,
                "full_text": "\n\n".join(paragraphs),
                "metadata": metadata
            }
        
        except Exception as e:
            logger.error(f"DOCX parsing error: {str(e)}")
            return {
                "source_id": metadata.get("id"),
                "source_type": "docx",
                "error": str(e),
                "metadata": metadata
            }

class ExcelParser(DocumentParser):
    """Parse Excel documents using pandas"""
    
    def parse(self, content: bytes, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract data from Excel"""
        
        try:
            excel_file = pd.ExcelFile(io.BytesIO(content))
            
            sheets = {}
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                sheets[sheet_name] = {
                    "rows": len(df),
                    "columns": list(df.columns),
                    "data": df.to_dict(orient="records")
                }
            
            return {
                "source_id": metadata.get("id"),
                "source_type": "excel",
                "title": metadata.get("title"),
                "sheets": sheets,
                "metadata": metadata
            }
        
        except Exception as e:
            logger.error(f"Excel parsing error: {str(e)}")
            return {
                "source_id": metadata.get("id"),
                "source_type": "excel",
                "error": str(e),
                "metadata": metadata
            }

class HTMLParser(DocumentParser):
    """Parse HTML content using BeautifulSoup"""
    
    def parse(self, content: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract text from HTML"""
        
        try:
            soup = BeautifulSoup(content, "html.parser")
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract text
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)
            
            return {
                "source_id": metadata.get("id"),
                "source_type": "html",
                "title": metadata.get("title"),
                "full_text": text,
                "metadata": metadata
            }
        
        except Exception as e:
            logger.error(f"HTML parsing error: {str(e)}")
            return {
                "source_id": metadata.get("id"),
                "source_type": "html",
                "error": str(e),
                "metadata": metadata
            }

class ParserFactory:
    """Factory for creating appropriate parser based on content type"""
    
    _parsers = {
        "application/pdf": PDFParser(),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DOCXParser(),
        "application/vnd.ms-excel": ExcelParser(),
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ExcelParser(),
        "text/html": HTMLParser()
    }
    
    @classmethod
    def get_parser(cls, content_type: str) -> DocumentParser:
        """Get parser for content type"""
        return cls._parsers.get(content_type)
    
    @classmethod
    def parse_document(
        cls,
        content: Any,
        content_type: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Parse document using appropriate parser"""
        
        parser = cls.get_parser(content_type)
        
        if parser is None:
            logger.warning(f"No parser for content type: {content_type}")
            return {
                "source_id": metadata.get("id"),
                "source_type": "unknown",
                "error": f"Unsupported content type: {content_type}",
                "metadata": metadata
            }
        
        return parser.parse(content, metadata)
```

### 4. Context Normalization

```python
# backend/app/mcp/normalizer.py
from typing import Dict, List, Any
import hashlib
from datetime import datetime

from .parsers import ParserFactory

class ContextNormalizer:
    """
    Normalize retrieved context into unified format.
    
    Features:
    - Unified document structure
    - Source ID assignment
    - Metadata extraction
    - Content chunking for LLM consumption
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def normalize_context_pack(
        self,
        context_pack: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Normalize context pack into list of normalized documents.
        
        Args:
            context_pack: Raw context pack from MCP connector
            
        Returns:
            List of normalized documents
        """
        
        normalized_docs = []
        
        # Normalize pages
        for page in context_pack.get("pages", []):
            parsed = ParserFactory.parse_document(
                content=page["content"],
                content_type="text/html",
                metadata=page
            )
            
            normalized = self._normalize_document(parsed, "confluence_page")
            normalized_docs.append(normalized)
        
        # Normalize attachments
        for attachment in context_pack.get("attachments", []):
            parsed = ParserFactory.parse_document(
                content=attachment["content"],
                content_type=attachment["media_type"],
                metadata=attachment
            )
            
            normalized = self._normalize_document(parsed, "confluence_attachment")
            normalized_docs.append(normalized)
        
        return normalized_docs
    
    def _normalize_document(
        self,
        parsed_doc: Dict[str, Any],
        doc_type: str
    ) -> Dict[str, Any]:
        """Normalize single document"""
        
        # Generate stable source ID
        source_id = self._generate_source_id(parsed_doc)
        
        # Extract full text
        full_text = parsed_doc.get("full_text", "")
        
        # Chunk content
        chunks = self._chunk_text(full_text)
        
        # Build normalized document
        normalized = {
            "source_id": source_id,
            "original_id": parsed_doc.get("source_id"),
            "doc_type": doc_type,
            "title": parsed_doc.get("title", "Untitled"),
            "full_text": full_text,
            "chunks": chunks,
            "chunk_count": len(chunks),
            "metadata": {
                **parsed_doc.get("metadata", {}),
                "normalized_at": datetime.utcnow().isoformat(),
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap
            }
        }
        
        # Add parsing errors if any
        if "error" in parsed_doc:
            normalized["parsing_error"] = parsed_doc["error"]
        
        return normalized
    
    def _generate_source_id(self, parsed_doc: Dict[str, Any]) -> str:
        """Generate stable source ID from document content"""
        
        # Use original ID if available
        if parsed_doc.get("source_id"):
            return f"src_{parsed_doc['source_id']}"
        
        # Otherwise, hash the content
        content = parsed_doc.get("full_text", "")
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return f"src_{content_hash}"
    
    def _chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Chunk text for LLM consumption with overlap.
        
        Args:
            text: Full text to chunk
            
        Returns:
            List of chunks with metadata
        """
        
        if not text:
            return []
        
        chunks = []
        start = 0
        chunk_id = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]
            
            chunks.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "start_char": start,
                "end_char": end,
                "length": len(chunk_text)
            })
            
            chunk_id += 1
            start = end - self.chunk_overlap
        
        return chunks
```

## Testing Phase 2

```python
# tests/test_mcp_connector.py
import pytest
from backend.app.mcp.connector import MCPConnector
from backend.app.mcp.config import MCPConfig, CONTEXT_RETRIEVAL_PROFILE

@pytest.mark.asyncio
async def test_mcp_connector():
    """Test MCP connector retrieval"""
    
    config = MCPConfig(
        base_url="https://your-domain.atlassian.net",
        bearer_token="your-token"
    )
    
    async with MCPConnector(config) as connector:
        context_pack = await connector.retrieve_context(CONTEXT_RETRIEVAL_PROFILE)
        
        assert context_pack["total_pages"] > 0
        assert "pages" in context_pack
        assert "metadata" in context_pack

@pytest.mark.asyncio
async def test_document_parsing():
    """Test document parser pipeline"""
    
    from backend.app.mcp.parsers import ParserFactory
    
    # Test PDF parsing
    with open("tests/fixtures/sample.pdf", "rb") as f:
        content = f.read()
    
    parsed = ParserFactory.parse_document(
        content=content,
        content_type="application/pdf",
        metadata={"id": "test_pdf", "title": "Test PDF"}
    )
    
    assert parsed["source_type"] == "pdf"
    assert "full_text" in parsed

@pytest.mark.asyncio
async def test_context_normalization():
    """Test context normalization"""
    
    from backend.app.mcp.normalizer import ContextNormalizer
    
    normalizer = ContextNormalizer(chunk_size=500, chunk_overlap=100)
    
    context_pack = {
        "pages": [
            {
                "id": "page1",
                "title": "Test Page",
                "content": "<html><body>Test content</body></html>",
                "space_key": "TEST"
            }
        ],
        "attachments": []
    }
    
    normalized = normalizer.normalize_context_pack(context_pack)
    
    assert len(normalized) == 1
    assert normalized[0]["doc_type"] == "confluence_page"
    assert "chunks" in normalized[0]
```

## Environment Variables

```bash
# .env
MCP_BASE_URL=https://your-domain.atlassian.net
MCP_BEARER_TOKEN=your-confluence-api-token
MCP_TIMEOUT=30
MCP_MAX_RETRIES=3
MCP_RATE_LIMIT_PER_MINUTE=60
```

## Success Criteria

- ✅ MCP connector successfully retrieves Confluence pages
- ✅ Multiple retrieval profiles work correctly
- ✅ Document parsers handle PDF, DOCX, Excel, HTML
- ✅ Context normalization produces unified format
- ✅ Source IDs are stable and traceable
- ✅ Content chunking works for LLM consumption
- ✅ Error handling and retry logic function properly
- ✅ Rate limiting prevents API throttling

## Next Steps

Proceed to **Phase 3: LangGraph Orchestration & State Management** to integrate the MCP connector with the agent workflow.