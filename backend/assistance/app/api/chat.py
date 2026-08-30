"""
Chat API Router

Handles the streaming chat endpoint for the Advanced Assistance service.
Supports both QUERY (draft RFC, safe+idempotent) and POST (fallback) methods.

Endpoint: QUERY /api/assistance/chat/{project_id}  →  text/event-stream SSE
Fallback:  POST  /api/assistance/chat/{project_id}  →  text/event-stream SSE

Wire format matches existing /api/orchestration/stream/{project_id}:
  event: thought      data: {"text": "..."}
  event: action       data: {"tool": "...", "input": "..."}
  event: observation  data: {"text": "..."}
  event: answer       data: {"text": "..."}   (streamed in chunks)
  event: error        data: {"message": "..."}
  event: done         data: {"project_id": "..."}
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..react_agent import get_react_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assistance", tags=["assistance-chat"])


# ── Request / Response models ────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Payload for the chat endpoint."""

    message: str = Field(
        description="The user's question or message.",
        min_length=1,
        max_length=4096,
    )
    project_id: Optional[str] = Field(
        default=None,
        description="Project identifier. Can also be provided as path param.",
    )


# ── SSE headers (matching main backend pattern) ──────────────────────────────

_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # Disable nginx buffering
    "Access-Control-Allow-Origin": "*",
}


# ── QUERY method handler (RFC draft-ietf-httpbis-safe-method-w-body) ─────────

async def _chat_handler(project_id: str, body: ChatRequest) -> StreamingResponse:
    """Shared handler for both QUERY and POST chat methods."""
    effective_project_id = project_id or body.project_id
    if not effective_project_id:
        raise HTTPException(status_code=422, detail="project_id is required")

    if not body.message.strip():
        raise HTTPException(status_code=422, detail="message cannot be empty")

    agent = get_react_agent()

    async def event_stream():
        """Generate SSE events from the ReAct agent."""
        try:
            async for chunk in agent.stream_response(
                project_id=effective_project_id,
                user_message=body.message,
            ):
                yield chunk
        except Exception as exc:
            logger.error(
                "chat SSE fatal error for project %s: %s",
                effective_project_id,
                exc,
                exc_info=True,
            )
            import json
            yield f"event: error\ndata: {json.dumps({'message': str(exc), 'fatal': True})}\n\n"

    logger.info(
        "Chat request: project=%s message_len=%d",
        effective_project_id,
        len(body.message),
    )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


# ── Route registration ───────────────────────────────────────────────────────

# QUERY method — safe + idempotent with a body (draft RFC)
# FastAPI registers via add_api_route; browser fetch() supports custom methods.
router.add_api_route(
    "/chat/{project_id}",
    _chat_handler,
    methods=["QUERY"],
    summary="Stream chat response via ReAct agent (QUERY method)",
    response_class=StreamingResponse,
)


# POST fallback — identical payload, zero other changes needed
@router.post(
    "/chat/{project_id}",
    summary="Stream chat response via ReAct agent (POST fallback)",
    response_class=StreamingResponse,
)
async def chat_post(project_id: str, body: ChatRequest) -> StreamingResponse:
    """
    POST fallback for environments that block the QUERY HTTP method.
    Identical payload and response to the QUERY endpoint.
    """
    return await _chat_handler(project_id, body)

# Made with Bob
