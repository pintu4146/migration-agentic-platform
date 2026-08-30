"""
Tool Registry

All LangChain @tool functions for the Advanced Assistance ReAct agent.
V1 tools are fully implemented.
V2 stubs raise NotImplementedError — they are registered so the LLM knows
they exist, but attempts to call them return a clear message.

Design rules (from ADVANCED_ASSISTANCE_PLAN.md):
- Tool functions are plain Python — no LangChain-specific internals in the logic
- All side-effects (HTTP, Qdrant, Redis) are delegated to the retriever / store / generator
- V2 stubs raise NotImplementedError with a clear message (not silent failures)
- Swapping AgentExecutor ↔ LangGraph ToolNode requires changing only react_agent.py
- Every @tool has a precise docstring (the LLM reads these to decide which tool to call)
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from .context_retriever import get_context_retriever
from .command_generator import get_command_generator
from .conversation_store import get_conversation_store
from .prompts import (
    SEARCH_STATE_DESC,
    SEARCH_QDRANT_DESC,
    GENERATE_COMMAND_DESC,
    INGEST_CONTEXT_DESC,
    FETCH_WORKFLOW_STATE_DESC,
)

logger = logging.getLogger(__name__)

# ── Embedder for Qdrant search ────────────────────────────────────────────────
# Lazy import to avoid loading OpenAI/Gemini SDK at module import time.
def _embed(text: str) -> List[float]:
    """
    Synchronous wrapper that generates an embedding for a query string.
    Uses openai text-embedding-3-small if available, else falls back to
    a zero vector (for tests / mock mode).
    """
    try:
        import os
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        resp = client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        return resp.data[0].embedding
    except Exception as exc:
        logger.warning("_embed: embedding failed (%s) — returning zero vector", exc)
        return [0.0] * 1536  # OpenAI text-embedding-3-small dimension


# ══════════════════════════════════════════════════════════════════════════════
# V1 TOOLS — Fully implemented
# ══════════════════════════════════════════════════════════════════════════════

@tool
def search_state(project_id: str, query: str, top_k: int = 5) -> str:
    """Search the extracted workflow state for migration facts.

    Searches across: extracted_facts, evidence_map, intake_draft,
    validation_results, review_flags, gap_analysis, confidence_scores.

    Use this FIRST before searching documents. Returns field name,
    snippet, and confidence score if available.

    Args:
        project_id: The project to search.
        query: Natural language search query (e.g. "spring security version").
        top_k: Maximum results to return (default 5).
    """
    retriever = get_context_retriever()
    results: List[Dict[str, Any]] = asyncio.get_event_loop().run_until_complete(
        retriever.search_state(project_id=project_id, query=query, top_k=top_k)
    )

    if not results:
        return f"No results found in workflow state for query: '{query}'"

    lines = [f"Found {len(results)} result(s) in workflow state:\n"]
    for r in results:
        conf = f" (confidence: {r['confidence']:.2f})" if r.get("confidence") else ""
        lines.append(f"[{r['field']}]{conf}\n{r['snippet']}\n")

    return "\n".join(lines)


@tool
def search_qdrant(
    project_id: str,
    query: str,
    top_k: int = 5,
    score_threshold: float = 0.5,
) -> str:
    """Semantic search over the project's embedded document chunks.

    Searches the Qdrant vector collection for this project (project_{project_id}).
    Use when search_state returns no results or low-confidence results.
    Includes source document metadata and similarity scores.

    Args:
        project_id: The project to search.
        query: Natural language search query.
        top_k: Maximum results (default 5).
        score_threshold: Minimum similarity score 0.0–1.0 (default 0.5).
    """
    retriever = get_context_retriever()
    embedding = _embed(query)

    results: List[Dict[str, Any]] = asyncio.get_event_loop().run_until_complete(
        retriever.search_qdrant(
            project_id=project_id,
            query_embedding=embedding,
            top_k=top_k,
            score_threshold=score_threshold,
        )
    )

    if not results:
        return (
            f"No document chunks found above score threshold {score_threshold} "
            f"for query: '{query}'"
        )

    lines = [f"Found {len(results)} chunk(s) in project documents:\n"]
    for r in results:
        src = r.get("metadata", {}).get("source", "unknown")
        lines.append(
            f"[score: {r['score']:.3f} | source: {src}]\n{r['text'][:400]}\n"
        )

    return "\n".join(lines)


@tool
def generate_command(
    question: str,
    reason: str,
    tech_context: Optional[str] = None,
) -> str:
    """Generate a diagnostic command for missing migration context.

    When neither state nor document search answers the question,
    generates a safe, copy-pasteable PowerShell/Bash/Maven/Gradle/Docker
    command the user can run locally and paste back into the chat.

    Args:
        question: The specific migration question needing more context.
        reason: Why current data is insufficient (e.g. "confidence 0.4, no evidence found").
        tech_context: Optional technology hints (e.g. "Java 11, Maven 3.8, Spring Boot 2.7").
    """
    generator = get_command_generator()
    cmd = asyncio.get_event_loop().run_until_complete(
        generator.generate(
            question=question,
            reason=reason,
            tech_context=tech_context,
        )
    )

    return (
        f"Suggested diagnostic command:\n"
        f"Shell: {cmd.shell}\n"
        f"```{cmd.shell}\n{cmd.command}\n```\n"
        f"Purpose: {cmd.purpose}\n"
        f"Expected output: {cmd.expected_output}\n"
        f"Paste the output back into the chat and I will ingest it."
    )


@tool
def ingest_context(
    project_id: str,
    text: str,
    context_type: str = "user_note",
) -> str:
    """Store user-provided context (e.g. command output) into the project knowledge base.

    Chunks, embeds, and stores the provided text into the project's Qdrant
    collection, tagged with source='user_assistance'. Use after the user
    pastes command output or additional documentation.

    Args:
        project_id: The project to ingest into.
        text: The text content to store (command output, doc paste, etc.).
        context_type: Label for the source (e.g. "command_output", "user_note", "doc_paste").
    """
    try:
        import os, uuid
        from datetime import datetime
        from openai import OpenAI
        from qdrant_client import QdrantClient
        from qdrant_client.models import PointStruct

        # Split into ~500-char chunks
        chunk_size = 500
        chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

        openai_key = os.environ.get("OPENAI_API_KEY")
        if not openai_key:
            return "Cannot ingest: OPENAI_API_KEY not set."

        oai = OpenAI(api_key=openai_key)
        qdrant = QdrantClient(
            host=os.environ.get("QDRANT_HOST", "localhost"),
            port=int(os.environ.get("QDRANT_PORT", "6333")),
        )
        collection = f"project_{project_id}"
        points = []
        for i, chunk in enumerate(chunks):
            emb_resp = oai.embeddings.create(
                model="text-embedding-3-small", input=chunk
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
                            "context_type": context_type,
                            "ingested_at": datetime.utcnow().isoformat(),
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
            context_type,
        )
        return (
            f"Successfully ingested {len(chunks)} chunk(s) into project "
            f"knowledge base (type: {context_type}). "
            "I can now search this content with search_qdrant."
        )

    except Exception as exc:
        logger.error("ingest_context: failed — %s", exc)
        return f"Ingestion failed: {exc}"


@tool
def fetch_workflow_state(project_id: str) -> str:
    """Fetch the full MigrationState from the main orchestration backend.

    Returns the complete workflow state dict including phase, version,
    all extracted facts, validation results, and review flags.
    Use to check overall project status or to surface summary information.

    Args:
        project_id: The project to fetch state for.
    """
    retriever = get_context_retriever()
    try:
        state: Dict[str, Any] = asyncio.get_event_loop().run_until_complete(
            retriever.fetch_workflow_state(project_id=project_id)
        )
        # Return a concise summary rather than the full blob
        summary_keys = [
            "phase", "state_version", "human_reviewed",
            "extracted_facts", "validation_results", "review_flags",
            "missing_questions", "confidence_scores",
        ]
        summary = {k: state.get(k) for k in summary_keys if state.get(k) is not None}
        import json as _json
        return _json.dumps(summary, indent=2, default=str)
    except RuntimeError as exc:
        return f"Could not fetch workflow state: {exc}"


# ══════════════════════════════════════════════════════════════════════════════
# V2 STUBS — Registered so LLM knows they exist; raise NotImplementedError
# ══════════════════════════════════════════════════════════════════════════════

@tool
def search_web(query: str) -> str:
    """Search the public web for migration-related information.

    [V2 — Not yet enabled]
    Will search the web for cloud migration best practices,
    version compatibility, CVE information, and vendor documentation.

    Args:
        query: Web search query string.
    """
    raise NotImplementedError(
        "search_web is not yet enabled (V2 feature). "
        "Use search_state or search_qdrant for project-specific context."
    )


@tool
def run_in_sandbox(code: str, language: str = "python") -> str:
    """Execute code in a sandboxed environment and return the output.

    [V2 — Not yet enabled]
    Will run safe, read-only scripts to analyse migration artifacts
    (e.g. parse pom.xml, analyse config files).

    Args:
        code: The code to execute.
        language: Language to run ('python', 'bash', 'powershell').
    """
    raise NotImplementedError(
        "run_in_sandbox is not yet enabled (V2 feature). "
        "Use generate_command to produce a command you can run locally."
    )


@tool
def fetch_url(url: str) -> str:
    """Fetch a URL and return its text content.

    [V2 — Not yet enabled]
    Will fetch Confluence pages, Swagger specs, or GitHub files
    and add them to the project knowledge base.

    Args:
        url: The URL to fetch.
    """
    raise NotImplementedError(
        "fetch_url is not yet enabled (V2 feature). "
        "Use ingest_context to paste content manually."
    )


# ── Tool registry list (used by react_agent.py) ───────────────────────────────

V1_TOOLS = [
    search_state,
    search_qdrant,
    generate_command,
    ingest_context,
    fetch_workflow_state,
]

V2_STUBS = [
    search_web,
    run_in_sandbox,
    fetch_url,
]

ALL_TOOLS = V1_TOOLS + V2_STUBS

# Made with Bob
