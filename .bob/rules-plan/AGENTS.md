# Plan Mode — Architecture Constraints (Non-Obvious Only)

## LangGraph + StateManager = two separate state stores
LangGraph uses its in-memory `MemorySaver` checkpointer for graph-level state. The custom `StateManager` persists state to Redis separately via `_sync_state_to_redis()` inside `WorkflowOrchestrator`. This dual-store design means Redis reflects the "last known good" state for UI polling, while LangGraph holds the live execution state. Do not collapse these into one.

## Human-review is a hard stop, not a node
The workflow pauses by routing to `"END"` (not a `human_review` node loop). Resume is done by calling `POST /api/orchestration/resume` which calls `workflow.resume()` feeding updated state back into the graph. Any architecture that tries to "poll" from inside the graph will hit the 25-node recursion limit.

## Providers must remain stateless
`ProviderFactory` holds one instance of each provider. Providers cannot store per-request state. The circuit-breaker failure counter in `ProviderFactory` is the only shared mutable state allowed.

## Qdrant embedding model is OpenAI-dependent
`backend/app/embeddings/` uses `text-embedding-3-small` from OpenAI. If switching to Gemini-only, the embedding pipeline must also be replaced. Qdrant vector dimensions are tied to this model.

## Project isolation is partially implemented
Redis keys are namespaced by `project_id` (`state:{project_id}`). Qdrant collection isolation per project is documented in `backend/MULTI_PROJECT_ARCHITECTURE.md` but not fully wired — the `context_retrieval_profile` has a template `"project_{project_id}"` that is not yet formatted at runtime.

## Checkpoints are in-memory only
`StateManager._checkpoints` is a dict in RAM (keeps last 10 per project). A server restart loses all checkpoints. The rollback API works only within the same process lifetime.

## Config validates at import — can break DI
`settings = Settings()` + validation runs when `app.config` is imported. Any attempt to mock settings after import will fail unless the mock is set up at the `os.environ` level before the import occurs. This affects FastAPI dependency injection for tests.

## SSE stream holds connections open
`/api/orchestration/stream/{project_id}` uses `asyncio.sleep(1)` polling loop to push updates. Each connected client holds a long-lived async generator. Scale planning must account for concurrent open SSE connections per project (one per browser tab).
