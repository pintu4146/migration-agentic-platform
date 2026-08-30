# AGENTS.md

This file provides guidance to agents when working with code in this repository.

## Project
IBM Migration Copilot — Agentic AI app that turns legacy application analysis into cloud migration plans. FastAPI backend + React frontend with LangGraph multi-agent orchestration.

## Commands

### Backend (run from `backend/`)
```bash
# Activate venv first
.\venv\Scripts\activate           # Windows
source venv/bin/activate          # Linux/Mac

# Start services (required before running backend)
podman-compose up -d              # Redis :6379, Qdrant :6333

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Tests (always run from backend/)
pytest                            # full suite with coverage
pytest tests/test_config.py -v   # single file
pytest -m unit                   # by marker: unit | integration | slow | provider
pytest tests/test_mcp.py::TestMCPConnector::test_health -v  # single test
```

### Frontend (run from `frontend/`)
```bash
npm run dev      # port 3000 (NOT 5173 — vite.config.js overrides default)
npm run build
npm run lint     # eslint, --max-warnings 0 (zero tolerance)
```

## Critical Non-Obvious Patterns

### State — NEVER write protected fields in patches
`state_version`, `created_at`, `updated_at`, `last_committed_by`, `last_committed_at`, `state_changelog` are blocked by `StateManager._validate_patch()`. Agents return a **patch dict** only; the state manager handles merging.

### LangGraph State Reducers — lists and dicts use custom merges
Fields annotated `Annotated[List[...], merge_lists]` (e.g., `normalized_docs`, `missing_questions`, `review_flags`) **append** on every update. Fields annotated `Annotated[Dict[...], merge_dicts]` (e.g., `trace_metadata`) do a shallow merge. Adding a new state field requires updating **both** `MigrationState` TypedDict **and** `create_initial_state()` in `backend/app/orchestration/state.py` — missing either causes `InvalidUpdateError`.

### Human-review pause — supervisor returns `"END"` not `"human_review"`
When `human_reviewed` is `False`, the supervisor routes to `"END"` to pause the LangGraph workflow. Routing back to the node causes infinite recursion (GraphRecursionError, limit=25). Resume via `POST /api/orchestration/resume` with `human_reviewed: true`.

### Gemini JSON — strip markdown code fences before parsing
Gemini wraps structured responses in ` ```json ... ``` `. The `GeminiProvider.generate_structured()` already strips these, but any code calling Gemini directly must handle this too.

### Config validates on import
`backend/app/config.py` calls `settings.validate_providers()` and `settings.validate_langsmith()` at module load. Tests must set env vars **before** any `from app.X import ...`. See `backend/tests/conftest.py` — env vars are set at the top of the file before imports.

### All components are singletons
`get_state_manager()`, `get_workflow_orchestrator()`, `get_supervisor()`, `get_context_retriever()`, `get_provider_factory()`, `get_tracer()` all return/create module-level singletons. `ProviderFactory.initialize()` must be awaited explicitly — the lifespan handler in `main.py` does this; tests must mock or await it themselves.

### Context retrieval fallback order: MCP → Qdrant
`ContextRetriever.retrieve()` tries MCP first, falls back to Qdrant automatically. Profile names passed to both share the same name (e.g., `"extraction_profile"`); the MCP version strips `_profile` suffix via `replace("_profile", "")`.

### SSE streaming endpoint
Real-time updates use `GET /api/orchestration/stream/{project_id}` (SSE). The frontend hook `useWorkflowSSE` listens for `state_update` and `phase_transition` named events (not generic `message` events). Polling fallback hook `useWorkflowPolling` also exists but SSE is preferred.

### Frontend API proxy
`vite.config.js` proxies `/api` and `/mcp` prefixes to `http://localhost:8000`. The `api.js` service uses `VITE_API_URL` env var (default `http://localhost:8000`). Direct fetch in `useWorkflowSSE` constructs the SSE URL from `API_BASE_URL` (same var).

### Qdrant collection naming
`context_retrieval_profile` in `qdrant_profiles.py` uses `"project_{project_id}"` as collection name (template literal, not yet formatted). Actual per-project collection names are `{project_id}_vectors` per `MULTI_PROJECT_ARCHITECTURE.md`.

### `@trace_operation` decorator
From `backend/app/tracing/langsmith.py` — wraps both sync and async functions with LangSmith `@traceable`. When tracing is disabled (`LANGCHAIN_TRACING_V2=false`), the original function is returned unwrapped. Used on nearly every agent method and state manager method.

## Code Style

### Python (backend)
- Pydantic v2 for all models; use `model_dump()` not `.dict()`
- All async functions; no blocking I/O
- Google-style docstrings with Args/Returns/Raises
- `logging.getLogger(__name__)` in every module
- Custom exceptions inherit from `Exception` and are module-local

### JavaScript (frontend)
- Functional React with hooks only — no class components
- IBM Carbon Design System components exclusively (no custom UI primitives)
- Each page/component has a co-located `.scss` file
- All API calls go through `frontend/src/services/api.js` — never fetch directly from components
- Workflow phase logic lives in `frontend/src/utils/workflowHelpers.js`

## File Ending Convention
Every file ends with `# Made with Bob` (Python) or `// Made with Bob` (JS). Maintain this.
