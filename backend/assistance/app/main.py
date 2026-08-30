"""
Advanced Assistance Service — FastAPI Entry Point

Standalone SOA microservice at port :8001.
Does NOT import anything from backend/app/ — communicates via HTTP only.

Startup order:
  1. Load config from environment
  2. Connect to Redis (conversation store)
  3. Register API routers
  4. Start Uvicorn on :8001
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.chat import router as chat_router
from .api.context import router as context_router
from .api.history import router as history_router
from .conversation_store import get_conversation_store
from .config import get_settings

logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service startup and graceful shutdown."""
    settings = get_settings()
    logger.info("Advanced Assistance Service starting up...")
    logger.info("Redis URL: %s", settings.redis_url)
    logger.info("Main backend: %s", settings.main_backend_url)
    logger.info("Qdrant: %s:%s", settings.qdrant_host, settings.qdrant_port)

    # Warm up conversation store (lazy Redis connect)
    store = get_conversation_store(redis_url=settings.redis_url)
    try:
        client = await store._get_client()
        pong = await client.ping()
        logger.info("Redis connection: %s", "OK" if pong else "FAILED")
    except Exception as exc:
        logger.warning("Redis not reachable at startup: %s — continuing anyway", exc)

    logger.info("Advanced Assistance Service ready on port %s", settings.port)
    yield

    # Shutdown
    logger.info("Advanced Assistance Service shutting down...")
    await store.close()
    logger.info("Advanced Assistance Service stopped.")


# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="IBM Migration Copilot — Advanced Assistance Service",
        description=(
            "ReAct conversational assistant at the Human Review gate. "
            "Provides streaming chat, context ingestion, and history management "
            "for migration project reviewers."
        ),
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ─────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS", "QUERY"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────
    app.include_router(chat_router)
    app.include_router(context_router)
    app.include_router(history_router)

    # ── Health check ──────────────────────────────────────────────────────
    @app.get("/health", tags=["health"])
    async def health():
        """Service health check."""
        return {
            "status": "ok",
            "service": "advanced-assistance",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
        }

    @app.get("/", tags=["health"])
    async def root():
        """Root endpoint — service info."""
        return {
            "service": "IBM Migration Copilot — Advanced Assistance",
            "port": settings.port,
            "endpoints": {
                "chat_query": "QUERY /api/assistance/chat/{project_id}",
                "chat_post":  "POST  /api/assistance/chat/{project_id}",
                "ingest":     "POST  /api/assistance/context/{project_id}",
                "history_get":"GET   /api/assistance/history/{project_id}",
                "history_del":"DELETE /api/assistance/history/{project_id}",
                "health":     "GET   /health",
                "docs":       "GET   /docs",
            },
        }

    return app


# ── Application instance ──────────────────────────────────────────────────────
app = create_app()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "backend.assistance.app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level="info",
    )

# Made with Bob
