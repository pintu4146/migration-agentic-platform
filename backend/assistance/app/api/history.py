"""
History API Router

Manages per-project conversation history for the Advanced Assistance service.

Endpoints:
  GET    /api/assistance/history/{project_id}          — retrieve recent history
  DELETE /api/assistance/history/{project_id}          — clear all history
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..conversation_store import get_conversation_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assistance", tags=["assistance-history"])


# ── Response models ───────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    """A single conversation message."""
    role: str
    content: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


class HistoryResponse(BaseModel):
    """Response for GET history."""
    project_id: str
    messages: List[ChatMessage]
    count: int
    total_stored: int


class ClearHistoryResponse(BaseModel):
    """Response for DELETE history."""
    project_id: str
    cleared: bool
    message: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/history/{project_id}",
    response_model=HistoryResponse,
    summary="Get conversation history for a project",
)
async def get_history(
    project_id: str,
    last_n: int = Query(default=20, ge=1, le=100, description="Number of recent messages"),
) -> HistoryResponse:
    """
    Retrieve the last N conversation messages for a project.

    Args:
        project_id: Project identifier.
        last_n: Number of messages to return (1–100, default 20).

    Returns:
        HistoryResponse with messages list.
    """
    store = get_conversation_store()

    try:
        messages = await store.get_history(project_id=project_id, last_n=last_n)
        total = await store.count(project_id=project_id)

        return HistoryResponse(
            project_id=project_id,
            messages=[
                ChatMessage(
                    role=m.get("role", "unknown"),
                    content=m.get("content", ""),
                    timestamp=m.get("timestamp", ""),
                    metadata=m.get("metadata"),
                )
                for m in messages
            ],
            count=len(messages),
            total_stored=total,
        )

    except Exception as exc:
        logger.error(
            "get_history: failed for project %s — %s", project_id, exc, exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {exc}")


@router.delete(
    "/history/{project_id}",
    response_model=ClearHistoryResponse,
    summary="Clear conversation history for a project",
)
async def clear_history(project_id: str) -> ClearHistoryResponse:
    """
    Delete all conversation history for a project.

    Args:
        project_id: Project identifier.

    Returns:
        ClearHistoryResponse confirming deletion.
    """
    store = get_conversation_store()

    try:
        await store.clear(project_id=project_id)
        logger.info("clear_history: cleared history for project %s", project_id)

        return ClearHistoryResponse(
            project_id=project_id,
            cleared=True,
            message=f"Conversation history cleared for project {project_id}.",
        )

    except Exception as exc:
        logger.error(
            "clear_history: failed for project %s — %s", project_id, exc, exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {exc}")

# Made with Bob
