# IBM Migration Copilot

> **Intelligent Application Modernization — from scattered legacy docs to a cloud migration plan, in hours not weeks.**

> **Latest**: Advanced Assistance Service planned at the Human Review gate — a Chain-of-Thought conversational assistant that reasons over extracted facts, searches project documents, and generates diagnostic commands when more context is needed. See [`docs/ADVANCED_ASSISTANCE_PLAN.md`](docs/ADVANCED_ASSISTANCE_PLAN.md).

---

## What Is This?

The IBM Migration Copilot is an **Agentic AI application** that automates the most painful parts of enterprise application migration:

1. **Ingesting** source documents — uploaded files (PDF, DOCX, pom.xml, .env, etc.) and Confluence pages via an IBM Context Studio MCP gateway
2. **Extracting** migration-relevant technical facts with AI confidence scoring and source evidence tracking
3. **Generating** a targeted questionnaire to fill knowledge gaps
4. **Drafting** a structured AS-IS intake document ready for human review
5. **Validating** the draft for completeness and consistency
6. **Pausing** for a human-in-the-loop review and approval gate — with a planned **Advanced Assistance** CoT chat panel for real-time Q&A over extracted facts and project documents
7. **Producing** a cloud migration plan with strategy, phased execution, and risk assessment

The entire pipeline is orchestrated by a **LangGraph supervisor-led multi-agent workflow** with full LangSmith traceability.

---

## Architecture

### High-Level System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  Browser (React + IBM Carbon)                                    │
│  :3000  ──SSE──▶  Workflow live updates                         │
│         ──REST─▶  /api/orchestration, /api/projects, /api/docs  │
└──────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│  FastAPI  :8000                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  WorkflowOrchestrator  (LangGraph StateGraph)           │    │
│  │                                                         │    │
│  │  [supervisor] ──▶ [context_retrieval] ──▶ [extraction] │    │
│  │       ▲                                        │        │    │
│  │       └──────────────────────────────────◀────┘        │    │
│  │       ▼                                                 │    │
│  │  [questionnaire] ──▶ [intake_draft] ──▶ [validation]   │    │
│  │                                               │         │    │
│  │                                    ──▶ [human_review]  │    │
│  │                                        (pause → END)   │    │
│  │                                               │(resume) │    │
│  │                                    ──▶ [migration_plan] │    │
│  │                                    ──▶ [complete]       │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ StateManager │  │ContextRetrvr │  │ LLM ProviderFactory   │  │
│  │ (Redis sync) │  │ (MCP→Qdrant) │  │ (OpenAI / Gemini)     │  │
│  └──────────────┘  └──────────────┘  └───────────────────────┘  │
└──────┬──────────────────┬────────────────────────────────────────┘
       │                  │
  ┌────▼────┐        ┌────▼────┐
  │  Redis  │        │ Qdrant  │
  │  :6379  │        │  :6333  │
  │ (state) │        │(vectors)│
  └─────────┘        └─────────┘
```

### Agent Roster

| Agent | File | Responsibility |
|-------|------|----------------|
| **Supervisor** | `orchestration/supervisor.py` | Deterministic routing between nodes; handles retry logic; pauses at human-review |
| **Context Retrieval** | `agents/context_retrieval_agent.py` | Calls `ContextRetriever` (MCP→Qdrant fallback); normalizes documents into state |
| **Extraction** | `agents/extraction_agent.py` | LLM-based structured fact extraction; assigns confidence scores; maps evidence |
| **Questionnaire** | `agents/questionnaire_agent.py` | Gap analysis; generates prioritized questions from low-confidence or missing facts |
| **Intake Draft** | `agents/intake_draft_agent.py` | Produces structured intake document from extracted facts |
| **Review/Validation** | `agents/review_validation_agent.py` | Checks for contradictions, unsupported claims, completeness |
| **Migration Planning** | `orchestration/workflow.py` node | *(Phase 6 — scaffolding only)* Cloud strategy recommendations |
| **Advanced Assistance** | `app/assistance/` *(planned)* | CoT conversational assistant at Human Review gate — layered context lookup, LLM-powered command generation, per-project Redis chat history |

### State Machine

Phases flow in this order:

```
INIT → CONTEXT_RETRIEVAL → EXTRACTION → QUESTIONNAIRE
     → INTAKE_DRAFT → VALIDATION → HUMAN_REVIEW (pause)
     → MIGRATION_PLANNING → COMPLETE
```

On error: up to 3 automatic retries from the last successful phase, then `ERROR` terminal state.

### Dual State Stores (Non-Obvious)

The system maintains **two** independent state representations:

- **LangGraph `MemorySaver`**: In-process graph checkpointer. Enables pause/resume across human-review gates.
- **Custom `StateManager` + Redis**: Transactional state with optimistic locking (version numbers), write-ahead changelog, and in-memory checkpoints. Drives the REST API and SSE stream for the UI.

The two are kept in sync inside `WorkflowOrchestrator._sync_state_to_redis()` after each graph step.

### LangGraph State Reducers

Fields in `MigrationState` that accumulate over time use custom `Annotated` reducers:

```python
# Lists append (never overwrite)
normalized_docs: Annotated[List[Dict], merge_lists]
missing_questions: Annotated[List[Dict], merge_lists]
review_flags: Annotated[List[str], merge_lists]
state_changelog: Annotated[List[StateChangelogEntry], merge_lists]

# Dicts shallow-merge (right wins on collision)
trace_metadata: Annotated[Dict[str, Any], merge_dicts]
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18, IBM Carbon Design System (`@carbon/react`), Vite, React Router v6 |
| **Backend** | FastAPI 0.109, Uvicorn, Pydantic v2, Python 3.11+ |
| **Orchestration** | LangGraph 0.0.20, LangChain 0.1.4 |
| **LLM Providers** | OpenAI (primary, `gpt-4-turbo-preview`), Google Gemini (fallback, `gemini-1.5-pro`) |
| **Observability** | LangSmith (every node, tool call, state transition traced) |
| **State / Cache** | Redis 7 (workflow state, session data) |
| **Vector Store** | Qdrant (document embeddings, semantic search fallback) |
| **Embeddings** | OpenAI `text-embedding-3-small` |
| **Document Parsing** | PyMuPDF (PDF), python-docx, pandas/openpyxl (Excel), custom text parsers |
| **MCP Connector** | IBM Context Studio Gateway (Confluence, SharePoint, etc.) |
| **Container Runtime** | Podman + Podman Compose |

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+** and npm
- **Podman** (for Redis and Qdrant containers)
- **Git**

---

## Quick Start

### 1. Clone and Configure

```bash
git clone <repository-url>
cd mig-26

# Copy and edit environment file
cp .env.example .env
# Fill in at minimum: OPENAI_API_KEY and LANGCHAIN_API_KEY
```

### 2. Start Container Services

```bash
cd backend
podman-compose up -d

# Verify
podman ps
# Expected: redis:7-alpine on :6379 and qdrant/qdrant on :6333
```

### 3. Backend

```bash
# From backend/
python -m venv venv
.\venv\Scripts\activate          # Windows
# source venv/bin/activate       # Linux/Mac

pip install -r requirements.txt

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at `http://localhost:8000/docs`

### 4. Frontend

```bash
# From frontend/ — in a new terminal
npm install
npm run dev
```

UI available at **`http://localhost:3000`** (not 5173 — port is overridden in `vite.config.js`)

### 5. Run Your First Migration Analysis

1. Open `http://localhost:3000`
2. **Dashboard → Create New Project** — enter a name and description
3. **Upload Documents** — drop in `pom.xml`, `application.properties`, architecture PDFs, etc.
4. **Start Workflow** — click "Start Workflow" then "Execute Next Step"
5. Watch real-time phase progression via SSE (⚡ Live Updates indicator)
6. At `human_review`, the workflow pauses automatically — click "Go to Review"
7. Review extracted facts, validation results, and review flags
8. *(Planned)* Use **Advanced Assistance** chat panel to ask questions about the extracted facts, request diagnostic commands, or upload additional context files
9. **Approve** the intake draft to trigger migration planning

---

## Environment Variables

All variables are documented in `.env.example`. Key groups:

### Required

```bash
# At least one LLM provider
OPENAI_API_KEY=sk-...
# or
GEMINI_API_KEY=...

# LangSmith (required if LANGCHAIN_TRACING_V2=true, which is the default)
LANGCHAIN_API_KEY=...
LANGCHAIN_PROJECT=migration-copilot-poc
```

### MCP Gateway (IBM Confluence/SharePoint)

```bash
MCP_GATEWAY_URL=https://servicesessentials.ibm.com/mcp-gateway/service/gateway/servers/<id>/mcp
MCP_GATEWAY_TOKEN=<bearer-token>
MCP_API_KEY=<context-studio-api-key>
```

Without MCP credentials the system silently falls back to Qdrant (uploaded documents only).

### Infrastructure (defaults match podman-compose)

```bash
REDIS_HOST=localhost    REDIS_PORT=6379
QDRANT_HOST=localhost   QDRANT_PORT=6333
```

### Provider Routing

```bash
PRIMARY_PROVIDER=openai    # or gemini
FALLBACK_PROVIDER=gemini   # or openai, or empty to disable fallback
```

---

## Advanced Assistance Service

The **Advanced Assistance Service** is a planned Chain-of-Thought (CoT) conversational assistant embedded at the Human Review pause point, built as a **standalone SOA microservice** (separate FastAPI app, own port `:8001`, own `Dockerfile`). Full specification: [`docs/ADVANCED_ASSISTANCE_PLAN.md`](docs/ADVANCED_ASSISTANCE_PLAN.md).

### What It Does

At the Human Review pause the reviewer can open a chat panel and ask natural language questions about the intake document. The assistant reasons in 4 visible steps:

```
User question
      │
      ▼
[Step 1] CHECK_STATE ── searches extracted_facts, evidence_map, intake_draft
      │  confidence ≥ 0.7 ──────────────────────────────────────────▶ ANSWER
      │  confidence < 0.7
      ▼
[Step 2] SEARCH_QDRANT ── semantic search over project_{project_id} collection
      │  confidence ≥ 0.6 ──────────────────────────────────────────▶ ANSWER
      │  confidence < 0.6
      ▼
[Step 3] REQUEST_CONTEXT ── LLM generates a targeted PowerShell/Maven command
      │  User runs command locally, pastes output (or uploads a file)
      │  Output is chunked + embedded + stored in Qdrant as source:"user_assistance"
      ▼
[Step 4] ANSWER ── synthesized response with source citations and confidence score
```

Every step is shown to the user as a live thinking trace (collapsible per message).

### SOA Architecture

The service is deployed independently from the main backend — its own process, own port, own container:

```
┌──────────────────────────────────────────────────────────────────────┐
│  Browser (React + IBM Carbon)  :3000                                 │
│                                                                      │
│  /api/assistance/* ──▶ Vite proxy ──▶ Assistance Service  :8001     │
│  /api/*            ──▶ Vite proxy ──▶ Main Backend        :8000     │
└──────────────────────────────────────────────────────────────────────┘

backend/assistance/                    ← Standalone service directory
├── app/
│   ├── main.py                        ← Own FastAPI app, uvicorn port 8001
│   ├── api/
│   │   ├── chat.py                    ← QUERY /chat/{project_id} → SSE stream
│   │   ├── context.py                 ← POST  /context/{project_id}
│   │   └── history.py                 ← GET / DELETE /history/{project_id}
│   ├── assistant_agent.py             ← 4-step CoT orchestrator + SSE streaming
│   ├── context_retriever.py           ← Layered lookup: state HTTP call → Qdrant
│   ├── command_generator.py           ← LLM-powered diagnostic commands
│   ├── conversation_store.py          ← Per-project Redis chat history
│   └── prompts.py                     ← System prompts + prompt builders
├── requirements.txt                   ← Own dependency set (lighter than main)
└── Dockerfile                         ← Own container image
```

**SOA contract — cross-service communication rules:**

| Need | Method | Example |
|------|--------|---------|
| Read workflow state | HTTP `GET` to main backend | `GET http://localhost:8000/api/orchestration/state/{id}` |
| Store/read chat history | Direct Redis — key prefix `assistance:*` | `assistance:{project_id}:history` |
| Search/write vectors | Direct Qdrant — existing collection | `project_{project_id}` |
| Call LLM | Own `LLMProvider` instance | Same providers, independent config |
| ❌ Never | Python import across service boundary | `from app.orchestration...` is forbidden |

### Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Deployment boundary** | Standalone FastAPI service at `:8001` | Independent scale, deploy, and maintain; zero coupling to main workflow engine |
| **Cross-service calls** | HTTP only — no Python imports across boundary | True SOA contract; main backend refactors cannot break assistance service |
| **Chat HTTP method** | `QUERY` *(see note below)* | Safe + idempotent read with a request body — semantically correct for a question |
| **Streaming transport** | `fetch()` + `ReadableStream` on frontend | `QUERY` with body requires `fetch()`; same `text/event-stream` wire format as existing SSE |
| **Conversation scope** | Per `project_id`, persisted in Redis | Full isolation; history survives browser refresh |
| **Qdrant collection** | Reuses existing `project_{project_id}` | No new collections; user context sits alongside original docs |
| **Vite proxy** | Add `/api/assistance → :8001` rule before `/api → :8000` | Zero frontend URL changes; transparent to all components |

> **Note on HTTP `QUERY` method**: `QUERY` is defined in [draft-ietf-httpbis-safe-method-w-body](https://www.ietf.org/archive/id/draft-ietf-httpbis-safe-method-w-body-02.txt) as a safe, idempotent method that carries a request body — the semantically correct fit for a chat question (it is a read, not a write). It is not yet a ratified RFC. Implementation uses `fetch()` with `method: 'QUERY'` and reads the `text/event-stream` response body as a `ReadableStream`. FastAPI registers it via `add_api_route(..., methods=["QUERY"])`. **If `QUERY` is blocked by a proxy or CORS policy in any environment, the drop-in fallback is `POST` — identical payload, zero other changes required.**

### Planned API Endpoints

All paths below are served from the Assistance Service at `:8001` and reachable via the Vite proxy at `/api/assistance/...`

| Method | Path | Description |
|--------|------|-------------|
| `QUERY` | `/api/assistance/chat/{project_id}` | Body: `{question: str}` — returns `text/event-stream` of `AssistantStreamEvent` objects |
| `POST` | `/api/assistance/context/{project_id}` | Ingest command output (text) or file upload into Qdrant |
| `GET` | `/api/assistance/history/{project_id}` | Full per-project conversation history |
| `DELETE` | `/api/assistance/history/{project_id}` | Clear conversation history |
| `GET` | `/api/assistance/context/{project_id}` | List user-provided context documents |

### Frontend: `fetch()` + `ReadableStream` for `QUERY`

`EventSource` is GET-only, so the chat stream uses `fetch()` — same SSE wire format, different client API:

```js
// assistanceApi.js — reusable stream helper
export async function* streamChat(projectId, question) {
  const response = await fetch(`/api/assistance/chat/${projectId}`, {
    method: 'QUERY',                                // draft RFC — safe + idempotent
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split('\n\n');
    buffer = blocks.pop();                          // retain incomplete chunk
    for (const block of blocks) {
      const line = block.split('\n').find(l => l.startsWith('data: '));
      if (line) yield JSON.parse(line.slice(6));
    }
  }
}

// useAssistance.js — clean consumer
for await (const event of streamChat(projectId, question)) {
  if (event.event_type === 'thinking_step') { /* append to CoT trace  */ }
  if (event.event_type === 'answer_chunk')  { /* accumulate text      */ }
  if (event.event_type === 'done')          { /* finalise message     */ }
}
```

### Context Isolation per Project

| Store | Key / Collection | Content |
|-------|-----------------|---------|
| Redis | `assistance:{project_id}:history` | Conversation messages with full thinking traces and source citations |
| Qdrant | `project_{project_id}` (shared with main) | Original uploaded docs + user-provided context tagged `source:"user_assistance"` |

### Frontend Plan (Sub-Task 7)

The planned frontend adds a 4th **"Advanced Assistance"** tab to `HumanReview.jsx`:
- Streaming chat panel with per-message collapsible CoT trace
- Thinking steps rendered live as `QUERY` stream events arrive
- Command block with `CopyButton` + paste-output textarea
- IBM Carbon `FileUploader` for context file ingestion
- Context document list (sidebar) showing all ingested user context

New frontend files: `assistanceApi.js` (with `streamChat` helper), `useAssistance.js`, `AssistancePanel.jsx`.
Vite proxy: add `/api/assistance → :8001` rule before `/api → :8000` in `vite.config.js`.
Main backend (`backend/app/main.py`) **is not touched** — service is fully standalone.

### Implementation Order

```
Sub-Task 1 → ConversationStore          (Redis — assistance service, port 8001)
Sub-Task 2 → ContextRetriever           (HTTP call to main :8000 → Qdrant direct)
Sub-Task 3 → CommandGenerator           (LLM commands, own provider instance)
Sub-Task 4 → AssistantAgent             (4-step CoT orchestrator + SSE streaming)
Sub-Task 5 → Context Ingestion Endpoint (POST /context — Qdrant direct)
Sub-Task 6 → Standalone FastAPI app     (main.py :8001 + Dockerfile + podman-compose entry)
Sub-Task 7 → Frontend Panel             (AssistancePanel.jsx + assistanceApi.js + vite proxy)
Sub-Task 8 → Prompt Engineering         (5 test scenarios + ASSISTANCE_PROMPT_TESTING.md)
Sub-Task 9 → Integration tests          (end-to-end across both services + docs update)
```

---

## API Reference

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Basic liveness check |
| `GET` | `/health/providers` | LLM provider status (primary + fallback) |
| `GET` | `/api/orchestration/health` | Orchestrator + state manager readiness |

### Projects

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/projects/create` | `{name, description}` → create project |
| `GET` | `/api/projects/list` | List all projects |
| `GET` | `/api/projects/{id}` | Get project details |
| `DELETE` | `/api/projects/{id}` | Delete project and all state |

### Documents

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/documents/upload` | `multipart/form-data` with `file` + `project_id` |
| `GET` | `/api/documents/list/{project_id}` | List uploaded documents |
| `POST` | `/api/documents/search` | `{project_id, query, limit}` semantic search |
| `DELETE` | `/api/documents/{id}` | Delete document |

### Workflow Orchestration

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/orchestration/start` | Initialize workflow state `{project_id, mcp_profile, query}` — returns 409 if already exists |
| `POST` | `/api/orchestration/execute` | Run next workflow step `{project_id}` |
| `POST` | `/api/orchestration/resume` | Resume after human-review `{project_id, updates}` where `updates.human_reviewed=true` |
| `POST` | `/api/orchestration/reset` | Wipe and re-initialize state `{project_id}` |
| `GET` | `/api/orchestration/state/{project_id}` | Current state snapshot |
| **`GET`** | **`/api/orchestration/stream/{project_id}`** | **SSE stream — named events: `state_update`, `phase_transition`, `error`** |

### MCP

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/mcp/health` | MCP gateway connectivity |
| `POST` | `/mcp/retrieve` | `{project_id, profile}` direct context retrieval |

---

## Testing

### Backend

```bash
cd backend
.\venv\Scripts\activate

# Full suite (requires running containers)
pytest

# Single file
pytest tests/test_config.py -v

# Single test
pytest tests/test_mcp.py::TestMCPConnector::test_health -v

# By marker (no containers needed)
pytest -m unit

# Skip slow tests
pytest -m "not slow"

# Coverage report (generated automatically — see htmlcov/)
pytest --cov=app --cov-report=html
```

**Note**: `conftest.py` sets dummy env vars (`OPENAI_API_KEY=test-key`, `LANGCHAIN_TRACING_V2=false`) before any imports. Real API calls must be mocked.

### Frontend

```bash
cd frontend
npm run lint       # Zero-warning enforcement
```

No automated UI tests are currently configured. Manual checklist is in the root `README` testing section.

---

## Development Workflow

### Adding a New Workflow Phase

All five of these must be updated atomically:

1. **`backend/app/orchestration/state.py`** — add value to `WorkflowPhase` enum and field to `MigrationState` TypedDict with correct reducer annotation, and initialize in `create_initial_state()`
2. **`backend/app/orchestration/supervisor.py`** — add routing branch in `decide_next_node()` and update `_phase_to_node()` map
3. **`backend/app/orchestration/workflow.py`** — add graph node method `_<phase>_node()` and register in `_build_graph()`
4. **`frontend/src/utils/workflowHelpers.js`** — add phase to `phaseOrder` array and `phaseWeights` dict
5. **`backend/tests/conftest.py`** — add field to `sample_migration_state` fixture if needed

### Adding a New LLM Provider

1. Create `backend/app/providers/<name>_provider.py` implementing `LLMProvider` ABC (4 abstract methods: `generate`, `generate_structured`, `generate_with_tools`, `health_check`)
2. Register in `ProviderFactory._create_provider()` and `settings.get_provider_config()`
3. Add config fields to `Settings` in `backend/app/config.py`
4. Add to `.env.example`

### Gemini-Specific: JSON Parsing

Gemini wraps all structured responses in markdown code fences. `GeminiProvider.generate_structured()` strips these before `json.loads()`. Any code calling Gemini raw must do the same:

```python
content = content.strip()
if content.startswith("```json"):
    content = content[7:]
elif content.startswith("```"):
    content = content[3:]
if content.endswith("```"):
    content = content[:-3]
result = json.loads(content.strip())
```

### Agent Return Contract

Every agent `execute()` returns a **partial patch dict** — only the keys that changed. Never return the full state object.

```python
# ✅ Correct
return {
    "extracted_facts": facts,
    "phase": "questionnaire",
    "last_committed_by": self.agent_name,
    "last_committed_at": datetime.utcnow().isoformat()
}

# ❌ Wrong — will fail StateManager._validate_patch()
return {**full_state, "extracted_facts": facts}
```

### LangSmith Tracing

Decorate any operation you want traced:

```python
from ..tracing.langsmith import trace_operation

@trace_operation("my_operation", run_type="chain", tags=["my-agent"])
async def my_method(self, state: MigrationState) -> Dict[str, Any]:
    ...
```

When `LANGCHAIN_TRACING_V2=false`, the decorator is a no-op and the original function is returned unchanged.

---

## Data Flow

```
Documents / Confluence Pages
         │
         ▼
[Context Retrieval] ──MCP primary──▶ IBM Context Studio
         │           ──Qdrant fallback──▶ uploaded docs (vectorized)
         │
         ▼ normalized_docs[] in state
[Extraction Agent] ──LLM──▶ structured JSON
         │
         ▼ extracted_facts{category: [{fact, confidence, evidence}]}
[Questionnaire Agent] ──LLM──▶ gap questions sorted by priority
         │
         ▼ missing_questions[] in state
[Intake Draft Agent] ──LLM──▶ AS-IS intake document structure
         │
         ▼ intake_draft{} in state
[Review/Validation Agent] ──rule-based + LLM──▶ flags, validation_results
         │
         ▼ human_review phase (PAUSE)
[Human Review UI] ──approve/reject──▶ resumeWorkflow()
         │
         ▼ human_reviewed: true
[Migration Planning Agent] ──LLM──▶ migration_plan{}
         │
         ▼ COMPLETE
```

---

## Multi-Project Architecture

Each project is isolated by `project_id`:

| Store | Key Pattern |
|-------|-------------|
| Redis state | `state:{project_id}` |
| Redis session | `session:{user_id}:{project_id}:{session_id}` |
| Redis cache | `cache:context:{project_id}` |
| Qdrant collection | `{project_id}_vectors` |

See `backend/MULTI_PROJECT_ARCHITECTURE.md` for the full session-based design.

---

## Observability

### LangSmith Traces

Every workflow execution is traced in LangSmith:
- Each graph node execution
- Every LLM call (prompt, response, token usage)
- All state transitions (from/to phase, version, committer)
- Agent tool calls

Navigate to your LangSmith project (`LANGCHAIN_PROJECT` env var, default `migration-copilot-poc`) to see execution trees.

### Backend Logs

Structured JSON logs by default (`LOG_FORMAT=json`). Each log entry includes the agent name, phase, and project_id. Set `LOG_LEVEL=DEBUG` for verbose output including state diffs.

### State Changelog

Every state commit appends to `state_changelog[]`. The REST endpoint `GET /api/orchestration/state/{project_id}` returns this as part of the state — use it to audit exactly which agent changed what and when.

---

## Troubleshooting

### `InvalidUpdateError` from LangGraph

An agent returned a key not in `MigrationState`. Add the field to the TypedDict and initialize it in `create_initial_state()`.

### `GraphRecursionError: Recursion limit of 25 reached`

The supervisor is routing to a node instead of `"END"` when it should pause. Check `supervisor.py` — the `HUMAN_REVIEW` branch must return `next_node="END"` when `human_reviewed` is `False`.

### `StateTransactionError: Version mismatch`

Two coroutines committed to the same project simultaneously. The `StateManager._lock` should prevent this within one process. Check for concurrent API calls from the frontend (double-click on execute button).

### Containers not starting

```bash
podman ps -a
podman logs <container-id>
podman-compose down && podman-compose up -d
```

### Backend fails to import (`ValueError: At least one LLM provider...`)

`config.py` validates on import. Set `OPENAI_API_KEY` or `GEMINI_API_KEY` in `.env` before starting.

### LangSmith traces not appearing

Check `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` are set. The `setup_langsmith()` function in `app/tracing/langsmith.py` must be called before LangChain/LangGraph imports — the lifespan handler in `main.py` does this.

### Frontend not loading at localhost:3000

The Vite dev server is configured for port **3000** in `vite.config.js`, not the default 5173. Check for port conflicts: `netstat -ano | findstr :3000`.

---

## Known Limitations (Current POC Scope)

| Limitation | Impact |
|------------|--------|
| In-memory `MemorySaver` for LangGraph | Workflow state lost on server restart; cannot resume after restart |
| In-memory `StateManager._checkpoints` | Rollback not available after restart |
| Migration Planning agent is a placeholder | Phase 6 is scaffolding only; migration plan output is minimal |
| No authentication | Single-user, no access control |
| Qdrant per-project collection isolation | Documented but not fully wired for `context_retrieval_profile` |
| 43 third-party dependency vulnerabilities | Acceptable for POC; remediation planned for production |

---

## Roadmap

| Item | Status | Reference |
|------|--------|-----------|
| **Advanced Assistance Service** | 🚧 Planned (9 sub-tasks) | [`docs/ADVANCED_ASSISTANCE_PLAN.md`](docs/ADVANCED_ASSISTANCE_PLAN.md) |
| **Phase 6 — Migration Planning** | ⏳ Scaffolding only | [`docs/06-phase6-migration-planning.md`](docs/06-phase6-migration-planning.md) |
| **Phase 7 — UI Enhancements** | ⏳ Spec written | [`docs/07-phase7-frontend-ui.md`](docs/07-phase7-frontend-ui.md) |
| **Phase 8 — Testing & Demo** | ⏳ Spec written | [`docs/08-phase8-testing-demo.md`](docs/08-phase8-testing-demo.md) |
| **AWS Bedrock Migration** | 📚 POC plan ready | [`docs/AWS_BEDROCK_POC_PLAN.md`](docs/AWS_BEDROCK_POC_PLAN.md) |
| **Production hardening** | ⏳ Planned | PostgreSQL, Qdrant Cloud, OAuth2/OIDC, Kubernetes |

---

## Project Structure

```
mig-26/
├── backend/
│   ├── app/
│   │   ├── agents/          # 5 specialized agent modules
│   │   ├── api/             # FastAPI routers (orchestration, documents, projects, mcp)
│   │   │                    #   + assistance.py (planned — /api/assistance)
│   │   ├── assistance/      # (planned) CoT assistant service
│   │   │   ├── assistant_agent.py      # 4-step CoT orchestrator + SSE streaming
│   │   │   ├── context_retriever.py    # Layered state → Qdrant context lookup
│   │   │   ├── command_generator.py    # LLM-powered diagnostic command generation
│   │   │   ├── conversation_store.py   # Per-project Redis chat history
│   │   │   └── prompts.py              # System prompts + prompt builders
│   │   ├── mcp/             # IBM Context Studio connector + profiles
│   │   ├── models/          # Pydantic schemas (schemas.py)
│   │   ├── orchestration/   # LangGraph workflow, supervisor, state, state_manager
│   │   ├── parsers/         # Multi-format document parsers
│   │   ├── providers/       # LLM provider abstraction (OpenAI, Gemini, factory)
│   │   ├── storage/         # Redis client, Qdrant client + profiles
│   │   ├── tracing/         # LangSmith integration + @trace_operation decorator
│   │   ├── config.py        # Pydantic Settings (validates on import)
│   │   ├── logging_config.py
│   │   └── main.py          # FastAPI app + lifespan + health endpoints
│   ├── poc/                 # Standalone POC scripts (AWS Bedrock steps, prompt testing)
│   ├── tests/               # pytest suite (unit + integration markers)
│   ├── requirements.txt
│   ├── requirements-dev.txt # Adds black, isort, flake8, mypy
│   └── pytest.ini           # asyncio_mode=auto, coverage on app/
├── frontend/
│   ├── src/
│   │   ├── components/      # Shared Carbon UI components (+ co-located .scss)
│   │   │   └── ChatDrawer/  # Slide-in chat drawer prototype (MOCK_MODE flag)
│   │   ├── hooks/           # useWorkflowSSE (primary), useWorkflowPolling (fallback)
│   │   ├── pages/           # Dashboard, DocumentUpload, WorkflowExecution,
│   │   │                    #   ExtractedFacts, HumanReview (+ co-located .scss)
│   │   ├── services/api.js  # All HTTP calls — single axios instance
│   │   └── utils/           # workflowHelpers.js (phase logic, progress, activity log)
│   └── vite.config.js       # Port 3000; proxies /api and /mcp to :8000
├── docs/
│   ├── 00-architecture-overview.md
│   ├── 01–08-phase*.md              # Phase-by-phase design + implementation guides
│   ├── ADVANCED_ASSISTANCE_PLAN.md  # CoT assistant — 9-sub-task full spec
│   ├── AWS_BEDROCK_POC_PLAN.md      # Step-by-step Bedrock migration POC (8 steps, 12 problems)
│   ├── ASSISTANCE_ENTRY_POINTS_PLAN.md  # ChatDrawer + FAB implementation record
│   └── fixes/ workflow/ phase-wise/ # Fix summaries, workflow docs, phase completion notes
├── .agents/                 # AI agent persistent memory (CRITICAL_BUGS_MEMORY, CODING_STANDARDS, etc.)
├── podman-compose.yml       # Root-level compose (Redis + Qdrant)
├── .env.example             # All supported env vars with descriptions
├── onboarding-plan.md       # Agent onboarding — verified phase status, mandatory rules
└── AGENTS.md                # AI agent guidance (this project's onboarding doc)
```

---

## Acknowledgements

Built with [LangGraph](https://langchain-ai.github.io/langgraph/) · [LangSmith](https://smith.langchain.com/) · [IBM Carbon Design System](https://carbondesignsystem.com/) · [FastAPI](https://fastapi.tiangolo.com/) · [OpenAI](https://openai.com/) · [Google Gemini](https://ai.google.dev/)
