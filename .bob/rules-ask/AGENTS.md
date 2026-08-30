# Ask Mode — Documentation Context (Non-Obvious Only)

## Code Organization Surprises
- `backend/app/orchestration/` contains both the **workflow graph** (`workflow.py`) and the **transactional state manager** (`state_manager.py`) — they are separate; the graph uses the state manager but doesn't replace it
- `backend/app/orchestration/context_retrieval.py` is NOT an agent — it's a shared utility used by `backend/app/agents/context_retrieval_agent.py`
- `frontend/src/hooks/useWorkflowPolling.js` exists but is **superseded** by `useWorkflowSSE.js` — polling is a fallback, SSE is active

## Two env files
Root `.env.example` and `backend/.env.example` both exist. The backend reads its `.env` file (relative to `backend/` when run as `uvicorn app.main:app`). The root `.env` is for documentation/reference.

## Phase order is NOT 1:1 with agent execution
The `WorkflowPhase` enum includes `VALIDATION` which runs **between** `INTAKE_DRAFT` and `HUMAN_REVIEW` — not after human review. See `supervisor.py` for the actual routing order.

## Migration Planning agent is a placeholder
`backend/app/orchestration/workflow.py` `_migration_planning_node()` is mostly scaffolding. The full implementation is planned (Phase 6). Do not suggest it works end-to-end.

## Docs directory
`docs/` contains design docs by phase (00-08), plus standalone docs for SSE, LangSmith, observability, and fix summaries. `WORKFLOW_FIXES_SUMMARY.md` at root documents the three critical bugs found during Phase 4 integration.

## MCP Gateway is IBM-specific
The MCP connector talks to IBM Services Essentials (`servicesessentials.ibm.com`). `MCP_API_KEY` is a JWT containing a `default_context_id` (`ctx_b4043773b9c6`) that is hard-coded as the fallback in `config.py`. Without valid MCP credentials the system silently falls back to Qdrant.

## Vite dev port
The dev server runs on **port 3000** (not the Vite default 5173) — explicitly set in `frontend/vite.config.js`. CORS is configured for `localhost:3000` and `localhost:5173` in `.env.example`.
