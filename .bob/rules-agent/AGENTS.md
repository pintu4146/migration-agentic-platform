# Agent Mode — Coding Rules (Non-Obvious Only)

## State Machine Coupling
When adding a new workflow phase:
1. Add value to `WorkflowPhase` enum in `backend/app/orchestration/state.py`
2. Add field(s) to `MigrationState` TypedDict (same file) with correct Annotated reducer
3. Initialize fields in `create_initial_state()` (same file)
4. Add routing logic in `Supervisor.decide_next_node()` (`backend/app/orchestration/supervisor.py`)
5. Add graph node in `WorkflowOrchestrator._build_graph()` (`backend/app/orchestration/workflow.py`)
Missing any step causes `InvalidUpdateError` or `KeyError` at runtime.

## Adding a new LLM provider
Implement `LLMProvider` abstract class from `backend/app/providers/base.py` — four required methods: `generate`, `generate_structured`, `generate_with_tools`, `health_check`. Register in `ProviderFactory._create_provider()`. Provider must be **stateless** — the factory caches one instance and may route concurrent requests through it.

## Agent return contract
Every agent `execute()` must return a **partial state patch dict**. Keys not in the dict are left unchanged. Never return the full state. Returning a field not in `MigrationState` causes `InvalidUpdateError`.

## MCP profile name normalization
`ContextRetriever._try_mcp()` calls `profile_name.replace("_profile", "")` before lookup. Pass the full name (e.g., `"extraction_profile"`) everywhere — the stripping is done internally, not by callers.

## Redis key namespace
State is stored as `state:{project_id}`. Sessions follow `session:{user_id}:{project_id}:{session_id}`. Never use bare keys — always namespace with the project_id prefix to prevent cross-project contamination.

## Test environment setup
Tests must set `os.environ` variables **before** any app import because `config.py` validates on import. Pattern lives in `backend/tests/conftest.py`. Use `pytest -m unit` to skip slow integration tests that require running containers.

## Frontend service layer
All HTTP calls must go through `frontend/src/services/api.js`. The axios instance is pre-configured with `baseURL`. Add new API functions to this file — never create ad-hoc `fetch()` or `axios.create()` elsewhere.

## SSE events — named, not generic
The SSE stream at `/api/orchestration/stream/{project_id}` emits named events: `state_update`, `phase_transition`, `error`. Use `eventSource.addEventListener('state_update', ...)` not `eventSource.onmessage`. See `backend/app/api/orchestration.py` `event_generator()`.
