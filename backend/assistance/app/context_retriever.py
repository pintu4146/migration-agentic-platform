"""
Context Retriever

Two retrieval strategies for the Advanced Assistance ReAct tools:
  1. search_state  — searches the structured MigrationState fields (Redis)
  2. search_qdrant — semantic vector search over project_{project_id} collection

Both are pure async functions with no dependency on backend/app/ Python modules.
Cross-service state access uses HTTP GET to the main backend at :8000.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

logger = logging.getLogger(__name__)

# Qdrant collection naming convention must match main backend exactly.
COLLECTION_PREFIX = "project_"

# Fields from MigrationState that are most useful for the assistant.
_SEARCHABLE_STATE_FIELDS = [
    "extracted_facts",
    "evidence_map",
    "intake_draft",
    "validation_results",
    "review_flags",
    "gap_analysis",
    "missing_questions",
    "confidence_scores",
]


class ContextRetriever:
    """
    Retrieves context from two sources:
    - Structured workflow state via HTTP from the main backend (:8000)
    - Semantic vector search via Qdrant

    Design:
    - No Python imports from backend/app/ — pure SOA via HTTP + direct Qdrant client
    - All methods are async
    - Returns serialisable dicts (no ORM / Pydantic models from main backend)
    """

    def __init__(
        self,
        main_backend_url: str = "http://localhost:8000",
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
    ):
        """
        Initialise the retriever.

        Args:
            main_backend_url: Base URL of the main FastAPI backend.
            qdrant_host: Qdrant server host.
            qdrant_port: Qdrant server port.
        """
        self._backend_url = main_backend_url.rstrip("/")
        self._qdrant_host = qdrant_host
        self._qdrant_port = qdrant_port
        self._qdrant: Optional[QdrantClient] = None

    # ── Qdrant ──────────────────────────────────────────────────────────

    def _get_qdrant(self) -> QdrantClient:
        """Lazy-initialise the Qdrant client (synchronous under the hood)."""
        if self._qdrant is None:
            self._qdrant = QdrantClient(
                host=self._qdrant_host,
                port=self._qdrant_port,
                timeout=10,
            )
            logger.info(
                "ContextRetriever: connected to Qdrant at %s:%s",
                self._qdrant_host,
                self._qdrant_port,
            )
        return self._qdrant

    # ── Public API ───────────────────────────────────────────────────────

    async def fetch_workflow_state(self, project_id: str) -> Dict[str, Any]:
        """
        Fetch full MigrationState dict from the main backend via HTTP.

        Args:
            project_id: Project identifier.

        Returns:
            State dict as returned by GET /api/orchestration/state/{project_id}.

        Raises:
            httpx.HTTPStatusError: If the main backend returns 4xx/5xx.
            RuntimeError: If the main backend is unreachable.
        """
        url = f"{self._backend_url}/api/orchestration/state/{project_id}"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                response.raise_for_status()
                state: Dict[str, Any] = response.json()
                logger.info(
                    "ContextRetriever: fetched state for project %s (phase=%s)",
                    project_id,
                    state.get("phase"),
                )
                return state
        except httpx.ConnectError as exc:
            logger.error(
                "ContextRetriever: cannot reach main backend at %s — %s", url, exc
            )
            raise RuntimeError(
                f"Main backend unreachable at {self._backend_url}. "
                "Ensure the orchestration service is running."
            ) from exc

    async def search_state(
        self,
        project_id: str,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search the structured MigrationState fields for the query string.

        Performs a simple case-insensitive substring scan across all
        searchable state fields. Returns matched snippets with field name
        and confidence score (if available).

        Args:
            project_id: Project identifier.
            query: Search query string.
            top_k: Maximum number of results to return.

        Returns:
            List of result dicts with keys: field, snippet, confidence.
        """
        state = await self.fetch_workflow_state(project_id)
        query_lower = query.lower()
        results: List[Dict[str, Any]] = []

        for field in _SEARCHABLE_STATE_FIELDS:
            value = state.get(field)
            if not value:
                continue

            # Flatten dict/list to a string representation for matching
            text = _flatten_to_text(value)
            if query_lower in text.lower():
                # Extract a short snippet around the match
                idx = text.lower().find(query_lower)
                start = max(0, idx - 120)
                end = min(len(text), idx + 300)
                snippet = ("..." if start > 0 else "") + text[start:end] + (
                    "..." if end < len(text) else ""
                )

                # Attempt to pull confidence from confidence_scores
                confidence: Optional[float] = None
                if field == "extracted_facts" and isinstance(value, dict):
                    scores = state.get("confidence_scores") or {}
                    for key in value:
                        if query_lower in key.lower():
                            confidence = scores.get(key)
                            break

                results.append(
                    {
                        "field": field,
                        "snippet": snippet,
                        "confidence": confidence,
                        "source": "workflow_state",
                    }
                )

            if len(results) >= top_k:
                break

        logger.info(
            "ContextRetriever: search_state '%s' → %d results for project %s",
            query,
            len(results),
            project_id,
        )
        return results

    async def search_qdrant(
        self,
        project_id: str,
        query_embedding: List[float],
        top_k: int = 5,
        score_threshold: float = 0.5,
        source_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic vector search over the project's Qdrant collection.

        Args:
            project_id: Project identifier (determines collection name).
            query_embedding: Pre-computed embedding vector for the query.
            top_k: Maximum results.
            score_threshold: Minimum cosine similarity score.
            source_filter: Optional metadata.source value to filter on.

        Returns:
            List of result dicts with keys: id, score, text, metadata.
        """
        collection = f"{COLLECTION_PREFIX}{project_id}"
        qdrant = self._get_qdrant()

        query_filter = None
        if source_filter:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="metadata.source",
                        match=MatchValue(value=source_filter),
                    )
                ]
            )

        try:
            hits = qdrant.search(
                collection_name=collection,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=query_filter,
                score_threshold=score_threshold,
            )
        except Exception as exc:
            logger.warning(
                "ContextRetriever: Qdrant search failed for '%s' — %s",
                collection,
                exc,
            )
            return []

        results = [
            {
                "id": str(hit.id),
                "score": round(hit.score, 4),
                "text": hit.payload.get("text", ""),
                "metadata": hit.payload.get("metadata", {}),
                "chunk_index": hit.payload.get("chunk_index", 0),
                "source": "qdrant",
            }
            for hit in hits
        ]

        logger.info(
            "ContextRetriever: search_qdrant → %d results (collection=%s)",
            len(results),
            collection,
        )
        return results


# ── Module helpers ────────────────────────────────────────────────────────────

def _flatten_to_text(value: Any, depth: int = 0) -> str:
    """Recursively flatten a dict / list / scalar to a single string."""
    if depth > 4:
        return str(value)
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            parts.append(f"{k}: {_flatten_to_text(v, depth + 1)}")
        return " | ".join(parts)
    if isinstance(value, list):
        return " ".join(_flatten_to_text(item, depth + 1) for item in value)
    return str(value)


# Module-level singleton
_retriever: Optional[ContextRetriever] = None


def get_context_retriever(
    main_backend_url: str = "http://localhost:8000",
    qdrant_host: str = "localhost",
    qdrant_port: int = 6333,
) -> ContextRetriever:
    """Return the module-level ContextRetriever singleton."""
    global _retriever
    if _retriever is None:
        _retriever = ContextRetriever(
            main_backend_url=main_backend_url,
            qdrant_host=qdrant_host,
            qdrant_port=qdrant_port,
        )
    return _retriever

# Made with Bob
