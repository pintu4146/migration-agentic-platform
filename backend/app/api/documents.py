"""
Document Upload API

Handles file uploads, parsing, chunking, and embedding generation.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel

from app.parsers.parser_factory import ParserFactory
from app.embeddings.chunker import DocumentChunker
from app.embeddings.embedder import EmbeddingGenerator
from app.storage.qdrant_store import QdrantStore
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


# Request/Response Models
class DocumentUploadResponse(BaseModel):
    """Response for document upload."""
    document_id: str
    file_name: str
    file_type: str
    file_size: int
    chunk_count: int
    chunks_created: int  # Alias for frontend compatibility
    parser_used: str
    stored_in: str
    status: str
    message: str


class DocumentListResponse(BaseModel):
    """Response for document list."""
    documents: List[Dict[str, Any]]
    total: int


class DocumentSearchRequest(BaseModel):
    """Request for document search."""
    query: str
    limit: int = 10
    filters: Optional[Dict[str, Any]] = None


class DocumentSearchResponse(BaseModel):
    """Response for document search."""
    results: List[Dict[str, Any]]
    total: int


# Dependency: Get Qdrant store
async def get_qdrant_store() -> QdrantStore:
    """Get Qdrant store instance."""
    store = QdrantStore()
    await store.initialize()
    return store


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    project_id: str = Form("default"),
    qdrant_store: QdrantStore = Depends(get_qdrant_store)
):
    """
    Upload and process a document.
    
    Steps:
    1. Save uploaded file temporarily
    2. Parse document using appropriate parser
    3. Chunk document content
    4. Generate embeddings
    5. Store in Qdrant
    6. Return document metadata
    """
    
    try:
        # Validate file type
        file_extension = Path(file.filename).suffix.lower()
        if not ParserFactory.is_supported(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_extension}"
            )
        
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Parse document
            logger.info(f"Parsing document: {file.filename}")
            parsed_doc = ParserFactory.parse_file(temp_path)
            
            # Get parser name from metadata
            parser_name = parsed_doc.get('metadata', {}).get('parser', 'unknown')
            
            # Add upload metadata
            parsed_doc['metadata']['uploaded_at'] = datetime.utcnow().isoformat()
            parsed_doc['metadata']['project_id'] = project_id
            parsed_doc['metadata']['file_size'] = len(content)
            
            # Chunk document
            logger.info(f"Chunking document: {file.filename}")
            chunker = DocumentChunker(
                chunk_size=settings.chunk_size,
                overlap=settings.chunk_overlap
            )
            chunks = chunker.chunk_document(parsed_doc)
            
            if not chunks:
                content_length = len(parsed_doc.get('content', ''))
                raise HTTPException(
                    status_code=400,
                    detail=f"Document produced no valid chunks. Extracted only {content_length} characters. "
                           f"This may be an image-based PDF or a document with minimal text content. "
                           f"Minimum chunk size is {settings.chunk_size} characters."
                )
            
            # Generate embeddings
            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            embedder = EmbeddingGenerator(provider_name=settings.default_provider)
            embedded_chunks = await embedder.embed_chunks(chunks)
            
            # Store in Qdrant
            logger.info(f"Storing {len(embedded_chunks)} chunks in Qdrant")
            document_id = f"{project_id}_{file.filename}_{datetime.utcnow().timestamp()}"
            collection_name = f"project_{project_id}"
            
            await qdrant_store.add_documents(
                documents=embedded_chunks,
                collection_name=collection_name
            )
            
            return DocumentUploadResponse(
                document_id=document_id,
                file_name=file.filename,
                file_type=file_extension,
                file_size=len(content),
                chunk_count=len(embedded_chunks),
                chunks_created=len(embedded_chunks),  # For frontend compatibility
                parser_used=parser_name,
                stored_in=collection_name,
                status="success",
                message=f"Document processed successfully with {len(embedded_chunks)} chunks"
            )
        
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )


@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(
    request: DocumentSearchRequest,
    project_id: str = "default",
    qdrant_store: QdrantStore = Depends(get_qdrant_store)
):
    """
    Search documents by semantic similarity.
    
    Args:
        request: Search request with query and filters
        project_id: Project ID for collection
        qdrant_store: Qdrant store instance
        
    Returns:
        Search results with scores
    """
    
    try:
        # Generate query embedding
        embedder = EmbeddingGenerator(provider_name=settings.default_provider)
        query_embedding = await embedder.embed_query(request.query)
        
        # Search in Qdrant
        results = await qdrant_store.search(
            query_embedding=query_embedding,
            collection_name=f"project_{project_id}",
            limit=request.limit,
            filters=request.filters
        )
        
        return DocumentSearchResponse(
            results=results,
            total=len(results)
        )
    
    except Exception as e:
        logger.error(f"Failed to search documents: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search documents: {str(e)}"
        )


@router.get("/list", response_model=DocumentListResponse)
async def list_documents(
    project_id: str = "default",
    qdrant_store: QdrantStore = Depends(get_qdrant_store)
):
    """
    List all documents in a project.
    
    Args:
        project_id: Project ID
        qdrant_store: Qdrant store instance
        
    Returns:
        List of document metadata
    """
    
    try:
        # Get all documents from collection
        documents = await qdrant_store.list_documents(
            collection_name=f"project_{project_id}"
        )
        
        return DocumentListResponse(
            documents=documents,
            total=len(documents)
        )
    
    except Exception as e:
        logger.error(f"Failed to list documents: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list documents: {str(e)}"
        )


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    project_id: str = "default",
    qdrant_store: QdrantStore = Depends(get_qdrant_store)
):
    """
    Delete a document and its chunks.
    
    Args:
        document_id: Document ID
        project_id: Project ID
        qdrant_store: Qdrant store instance
        
    Returns:
        Deletion status
    """
    
    try:
        # Delete from Qdrant
        deleted_count = await qdrant_store.delete_document(
            document_id=document_id,
            collection_name=f"project_{project_id}"
        )
        
        return {
            "status": "success",
            "message": f"Deleted {deleted_count} chunks",
            "document_id": document_id
        }
    
    except Exception as e:
        logger.error(f"Failed to delete document: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )


# Made with Bob