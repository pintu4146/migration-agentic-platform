"""
Context Ingestion API Router

Handles manual context ingestion at the Human Review gate.
Users can paste command output or additional documentation
which gets chunked, embedded, and stored in the project's Qdrant collection.

Endpoint: POST /api/assistance/context/{project_id}
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..context_retriever import get_context_retriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assistance", tags=["assistance-context"])


# ── Request / Response models ────────────────────────────────────────────────

class IngestContextRequest(BaseModel):
    """Payload for the context ingestion endpoint."""

    text: str = Field(
        description="Text content to ingest (command output, doc paste, etc.).",
        min_length=10,
        max_length=50_000,
    )
    context_type: str = Field(
        default="user_note",
        description="Label for the source: command_output | user_note | doc_paste | other.",
    )
    source_label: Optional[str] = Field(
        default=None,
        description="Optional human-readable label for this content (e.g. 'mvn dependency:tree output').",
    )


class IngestContextResponse(BaseModel):
    """Response after successful context ingestion."""

    project_id: str
    chunks_added: int
    context_type: str
    ingested_at: str
    message: str


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post(
    "/context/{project_id}",
    response_model=IngestContextResponse,
    summary="Ingest user-provided context into project knowledge base",
)
async def ingest_context(
    project_id: str,
    body: IngestContextRequest,
) -> IngestContextResponse:
    """
    Chunk, embed, and store user-provided text into the project's Qdrant collection.

    Text is tagged with:
    - metadata.source = "user_assistance"
    - metadata.context_type = body.context_type
    - metadata.project_id = project_id

    This makes user-provided content searchable via the search_qdrant tool
    and distinguishable from document-pipeline content.

    Args:
        project_id: Project identifier (determines Qdrant collection name).
        body: IngestContextRequest with text and context_type.

    Returns:
        IngestContextResponse with chunks_added count.
    """
    try:
        import os
        import uuid
        from openai import AsyncOpenAI
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct

        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            raise HTTPException(
                status_code=503,
                detail="OPENAI_API_KEY not configured — cannot generate embeddings.",
            )

        oai = AsyncOpenAI(api_key=openai_key)
        qdrant = QdrantClient(
            host=os.environ.get("QDRANT_HOST", "localhost"),
            port=int(os.environ.get("QDRANT_PORT", "6333")),
            timeout=15,
        )

        # Chunk at ~500 characters with 50-char overlap
        chunk_size = 500
        overlap = 50
        text = body.text
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            start += chunk_size - overlap

        now = datetime.utcnow().isoformat()
        collection = f"project_{project_id}"
        points = []

        for i, chunk in enumerate(chunks):
            emb_resp = await oai.embeddings.create(
                model="text-embedding-3-small",
                input=chunk,
            )
            embedding = emb_resp.data[0].embedding

            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "text": chunk,
                        "chunk_index": i,
                        "metadata": {
                            "source": "user_assistance",
                            "context_type": body.context_type,
                            "source_label": body.source_label or body.context_type,
                            "ingested_at": now,
                            "project_id": project_id,
                        },
                    },
                )
            )

        qdrant.upsert(collection_name=collection, points=points)

        logger.info(
            "ingest_context: stored %d chunks for project %s (type=%s)",
            len(points),
            project_id,
            body.context_type,
        )

        return IngestContextResponse(
            project_id=project_id,
            chunks_added=len(points),
            context_type=body.context_type,
            ingested_at=now,
            message=(
                f"Successfully stored {len(points)} chunk(s). "
                "The assistant can now search this content."
            ),
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "ingest_context: failed for project %s — %s", project_id, exc, exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Context ingestion failed: {exc}",
        )

# Made with Bob
