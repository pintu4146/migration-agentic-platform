# Advanced Assistance Service — Plan

**Feature**: A ReAct (Reason + Act) powered conversational assistant embedded at the Human Review pause point.
**Scope**: Standalone SOA microservice (`backend/assistance/`, port `:8001`). Frontend panel as 4th tab in `HumanReview.jsx`.
**Reasoning engine**: LangChain `ReActAgentExecutor` now — swap path to LangGraph `ToolNode` documented and preserved.
**Project Status prerequisite**: Phases 1–5 complete and stable. Human Review pause is fully wired.

---

## Top-Level Overview

At the Human Review pause, the user reviews extracted facts, validation results, and the intake draft. Often they have questions: *"Why was this dependency flagged?"*, *"What does the confidence score of 0.5 mean for this fact?"*, *"Is there any more detail about the database layer?"*

The **Advanced Assistance Service** provides a streaming **ReAct (Reason + Act)** conversational assistant that:

1. **Reasons visibly** — the LLM emits a `Thought` before every action; the full Thought/Action/Observation trace is streamed live to the UI
2. **Acts through a tool registry** — each capability is a declared LangChain `@tool`; the LLM picks which tool to call, in what order, for how many turns
3. **Stores context persistently per project** — conversation history and user-provided outputs stored in Redis + Qdrant under `project_id`
4. **Asks for more context intelligently** — `generate_command` tool produces targeted PowerShell/Maven commands; output ingested back via `ingest_context` tool
5. **Is future-ready** — adding a new capability (web search, sandbox, external docs) = add one `@tool` function; the LLM uses it automatically, no changes to the agent loop
6. **Is swap-safe** — tool functions are plain Python with no LangChain-specific internals; swapping `AgentExecutor` for LangGraph `ToolNode` requires changing only `react_agent.py`

### Reasoning Engine: ReAct vs Fixed CoT

| | Fixed CoT Pipeline (discarded) | ReAct (adopted) |
|--|--|--|
| **Reasoning** | Fixed 4-step waterfall: CHECK_STATE → SEARCH_QDRANT → REQUEST_CONTEXT → ANSWER | Dynamic: LLM decides next action based on each Observation |
| **Tool invocation** | Hardcoded in pipeline stages | LLM selects from declared tool registry |
| **Multi-step loops** | No — linear, single pass | Yes — LLM can call multiple tools, revisit context |
| **Adding new tools** | New pipeline stage + routing logic | One new `@tool` function |
| **Future: web search** | Major refactor | `@tool search_web(query)` |
| **Future: code sandbox** | Major refactor | `@tool run_in_sandbox(code)` |
| **Transparency** | 4 fixed step labels | Full Thought/Action/Observation trace per turn |

### ReAct Loop (How It Runs)

```
User question
      │
      ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ReAct Agent Loop  (LangChain AgentExecutor)                        │
│                                                                     │
│  Thought: "I should check extracted facts first"                    │
│  Action:  search_state("spring-security version")                   │
│  Obs:     "spring-security 5.7, confidence 0.82, source: pom.xml"  │
│                                                                     │
│  Thought: "Confidence is high. I can answer directly."              │
│  Action:  final_answer("Spring Security 5.7 is present…")          │
│                                                                     │
│  ── OR if confidence low ────────────────────────────────────────── │
│                                                                     │
│  Thought: "State search insufficient. Try project documents."       │
│  Action:  search_qdrant("spring-security transitive deps")          │
│  Obs:     "No chunks above threshold 0.6"                           │
│                                                                     │
│  Thought: "Need more context. Generate a diagnostic command."       │
│  Action:  generate_command("list maven dependencies")               │
│  Obs:     DiagnosticCommand(cmd="mvn dependency:tree …")            │
│                                                                     │
│  → Return needs_more_context=True + command block to frontend       │
└─────────────────────────────────────────────────────────────────────┘
      │
      ▼
Each Thought/Action/Obs streamed as SSE event → collapsible trace in UI
```

### Tool Registry

| Tool | Phase | Input | Output | Description |
|------|-------|-------|--------|-------------|
| `search_state` | **V1** | `query: str` | matching facts + confidence | Search `extracted_facts`, `evidence_map`, `intake_draft`, `validation_results` |
| `search_qdrant` | **V1** | `query: str` | top-k chunks + scores | Semantic search over `project_{project_id}` collection |
| `generate_command` | **V1** | `question: str, reason: str` | `DiagnosticCommand` | LLM-generates PowerShell/Maven/Java command for missing context |
| `ingest_context` | **V1** | `text: str, context_type: str` | `chunks_added: int` | Chunk + embed + store user output into Qdrant |
| `fetch_workflow_state` | **V1** | `project_id: str` | `MigrationState` dict | HTTP GET to main backend `:8000` |
| `search_web` | **V2 stub** | `query: str` | search results | Web search for latest migration docs, CVEs, changelogs |
| `run_in_sandbox` | **V2 stub** | `code: str, language: str` | stdout + stderr | Execute code in isolated sandbox |
| `fetch_url` | **V2 stub** | `url: str` | cleaned page text | Fetch official docs, RFC pages, release notes |

V2 tools are declared with `@tool` and raise `NotImplementedError("V2 — not yet implemented")`. The LLM sees them in the registry; their descriptions guide it to understand future capabilities without breaking current operation.

### LangChain → LangGraph Swap Path

```python
# react_agent.py — the ONLY file that changes in the swap

# ── Current: LangChain AgentExecutor ─────────────────────────────────
from langchain.agents import AgentExecutor, create_react_agent
from .tools import ALL_TOOLS   # same list in both versions

agent = create_react_agent(llm, ALL_TOOLS, react_prompt)
executor = AgentExecutor(agent=agent, tools=ALL_TOOLS, verbose=True)

# ── Future: LangGraph ToolNode ────────────────────────────────────────
from langgraph.prebuilt import ToolNode, create_react_agent   # LG version
from .tools import ALL_TOOLS   # UNCHANGED

executor = create_react_agent(llm, ALL_TOOLS)   # LangGraph version
# tools.py, prompts.py, chat.py, API — all UNCHANGED
```

### Key Design Decisions

- **SOA microservice** — standalone FastAPI at `:8001`; no Python imports from main backend
- **ReAct engine** — `LangChain AgentExecutor` now; `LangGraph ToolNode` later; only `react_agent.py` changes
- **Tool registry in `tools.py`** — all capabilities declared here; new tools added without touching agent loop
- **QUERY HTTP method** — safe + idempotent chat endpoint; `fetch()` + `ReadableStream` on frontend
- **Conversation stored in Redis** — key: `assistance:{project_id}:history`; per-project isolation
- **Qdrant reuse** — same `project_{project_id}` collection; user context tagged `source:"user_assistance"`
- **No changes to existing orchestration** — assistant is a separate read path; state accessed via HTTP only

---

## Architecture: How It Fits In

```
HumanReview.jsx
├── [Existing] Intake Draft Viewer tab
├── [Existing] Validation Results tab
├── [Existing] Review Flags tab
└── [NEW] Advanced Assistance tab
      ├── Chat history panel (scrollable)
      ├── Thought/Action/Observation trace (collapsible per message)
      ├── Message input + Send
      ├── File upload drop zone  ──▶ ingest_context tool
      └── "Run this command" block ──▶ generate_command tool output

frontend/src/services/assistanceApi.js
└── [NEW] streamChat() QUERY helper, getHistory(), uploadContext()

backend/assistance/                        ← Standalone SOA service, port 8001
├── app/
│   ├── main.py                            ← FastAPI app entry point
│   ├── api/
│   │   ├── chat.py                        ← QUERY /chat/{project_id} → SSE stream
│   │   ├── context.py                     ← POST  /context/{project_id}
│   │   └── history.py                     ← GET / DELETE /history/{project_id}
│   ├── react_agent.py                     ← AgentExecutor (SWAP POINT for LangGraph)
│   ├── tools.py                           ← @tool registry — V1 implemented, V2 stubs
│   ├── context_retriever.py               ← search_state + search_qdrant implementations
│   ├── command_generator.py               ← generate_command implementation
│   ├── conversation_store.py              ← Redis chat history per project
│   └── prompts.py                         ← ReAct system prompt + tool descriptions
├── requirements.txt
└── Dockerfile
```

---

## Sub-Task 1: Conversation Store (Redis, Per-Project)

**Intent**: Build the persistence layer for conversation history. Each project gets its own isolated conversation thread, stored in Redis, preserved across browser sessions. This is a prerequisite for all other sub-tasks.

**Expected Outcomes**:
- `ConversationStore` class in `backend/app/assistance/conversation_store.py`
- Per-project Redis key: `assistance:{project_id}:history`
- Stores messages as ordered list: `[{role, content, thinking_trace, timestamp, sources_used}]`
- Get/append/clear operations work correctly
- TTL matches existing `settings.redis_ttl`
- Unit test verifies isolation: project A history does not bleed into project B

**Todo List**:
1. Create `backend/app/assistance/` directory with `__init__.py`
2. Create `backend/app/assistance/conversation_store.py`:
   - Class `ConversationStore` with `redis_client: RedisClient` dependency
   - `async get_history(project_id) -> List[ConversationMessage]`
   - `async append_message(project_id, message: ConversationMessage) -> None`
   - `async clear_history(project_id) -> None`
   - `ConversationMessage` Pydantic model: `role` (user/assistant), `content`, `thinking_trace: List[ThinkingStep]`, `timestamp`, `sources_used: List[str]`
   - `ThinkingStep` Pydantic model: `step_number`, `action` (CHECK_STATE / SEARCH_QDRANT / REQUEST_CONTEXT / ANSWER), `description`, `result`, `confidence: float`
3. Use existing `RedisClient` from `backend/app/storage/redis_client.py` — do not create a new Redis connection
4. Key format: `assistance:{project_id}:history` (separate from `state:{project_id}`)
5. Serialize/deserialize using `json.dumps`/`json.loads` with `DateTimeEncoder` (already in redis_client.py)
6. Write unit test `backend/tests/test_assistance_store.py`

**Relevant Context**:
- `backend/app/storage/redis_client.py` — `RedisClient.get()`, `.set()`, `.delete()` methods; `DateTimeEncoder` for safe datetime serialization
- `backend/app/config.py` — `settings.redis_ttl` for TTL
- Redis key pattern for workflow state: `state:{project_id}` — use same pattern, different prefix

**Status**: `[ ] pending`

---

## Sub-Task 2: Layered Context Retriever

**Intent**: Build the core "context lookup" module that the assistant agent uses. It implements the three-layer strategy: state data first → Qdrant search second → insufficient signal. This is the brain of the context strategy — separate from the agent so it can be tested and improved independently.

**Expected Outcomes**:
- `ContextRetriever` class in `backend/app/assistance/context_retriever.py`
- Returns structured `ContextResult` with: `found_in` (state/qdrant/none), `content`, `confidence`, `sources`
- State lookup checks `extracted_facts`, `evidence_map`, `intake_draft`, `validation_results` from `MigrationState`
- Qdrant lookup queries the EXISTING `project_{project_id}` collection (same collection documents were uploaded to)
- Returns `confidence` score so the agent can decide whether to ask for more context
- Unit test with mocked state and mocked Qdrant verifies all three fallback paths

**Todo List**:
1. Create `backend/app/assistance/context_retriever.py`:
   - Class `ContextRetriever` with `qdrant_store: QdrantStore` and `embedder: EmbeddingGenerator` dependencies
   - `ContextResult` Pydantic model: `found_in: Literal["state", "qdrant", "none"]`, `content: str`, `confidence: float`, `sources: List[str]`, `raw_chunks: List[Dict]`
   - `async search_state(query, state: MigrationState) -> ContextResult`
     - Searches `extracted_facts` dict for keyword matches against query
     - Checks `evidence_map` for evidence references
     - Extracts relevant sections from `intake_draft`
     - Returns confidence based on number of matching facts and their existing confidence scores
   - `async search_qdrant(query, project_id) -> ContextResult`
     - Embeds query with existing `EmbeddingGenerator.embed_query()`
     - Calls `QdrantStore.search(query_embedding, collection_name=f"project_{project_id}", limit=5, score_threshold=0.6)`
     - Returns top chunks with score as confidence
   - `async get_context(query, state, project_id) -> Tuple[ContextResult, List[ThinkingStep]]`
     - Implements the layered strategy: try state → if confidence < 0.7 try Qdrant → return result with thinking trace
2. Reuse `backend/app/embeddings/embedder.py` `EmbeddingGenerator` — do not create new embedding logic
3. Reuse `backend/app/storage/qdrant_store.py` `QdrantStore` — do not create new Qdrant client
4. Write unit test `backend/tests/test_assistance_retriever.py`

**Relevant Context**:
- `backend/app/storage/qdrant_store.py` — `search()` signature: `(query_embedding, collection_name, limit, filters, score_threshold)`; collection naming: `project_{project_id}`
- `backend/app/embeddings/embedder.py` — `embed_query(query)` returns `List[float]`
- `backend/app/orchestration/state.py` — `MigrationState` TypedDict; all fields available at Human Review pause: `extracted_facts`, `confidence_scores`, `evidence_map`, `intake_draft`, `validation_results`, `review_flags`, `missing_questions`, `gap_analysis`
- `backend/app/orchestration/state_manager.py` — `get_state(project_id)` to read current state

**Status**: `[ ] pending`

---

## Sub-Task 3: Command Generator

**Intent**: Build the module that generates specific, executable diagnostic commands when the assistant determines that neither state data nor Qdrant have sufficient context. These commands are targeted to Java/Maven/Spring projects (the migration use case) and are generated based on the question being asked, not hardcoded.

**Expected Outcomes**:
- `CommandGenerator` class in `backend/app/assistance/command_generator.py`
- Takes a question + what context was insufficient → returns a `DiagnosticCommand` with `command`, `shell`, `description`, `expected_output_hint`
- LLM-powered: generates the right command for the question using a focused prompt
- Supports: Maven dependency tree, project structure (`tree`), Spring config extraction, Java class listing, log file search
- Commands are PowerShell-safe (Windows-first, since dev environment is Windows)
- Unit test verifies that the returned command is a non-empty string and shell is valid

**Todo List**:
1. Create `backend/app/assistance/command_generator.py`:
   - `DiagnosticCommand` Pydantic model: `command: str`, `shell: Literal["powershell", "bash", "cmd"]`, `description: str`, `expected_output_hint: str`, `context_type: Literal["dependency_tree", "project_structure", "java_class", "config_file", "log_file", "other"]`
   - Class `CommandGenerator` with `llm: LLMProvider` dependency
   - `async generate_command(question: str, missing_context_reason: str, project_tech_stack: Dict) -> DiagnosticCommand`
     - Builds a focused prompt: system = "You are an expert Java/Maven/Spring developer" + question + what context is missing
     - Calls `llm.generate_structured()` with `DiagnosticCommand` schema
     - Always generates PowerShell-compatible commands when possible
   - Include pre-built templates for common cases:
     - Maven dep tree: `mvn dependency:tree -Doutput=dep-tree.txt`
     - Project structure: `tree /F /A > project-structure.txt`
     - Spring config: `Get-Content src\main\resources\application.properties`
     - Java class listing: `Get-ChildItem -Recurse -Filter "*.java" | Select-Object FullName`
2. Reuse provider from `backend/app/providers/factory.py` `get_provider()`
3. Write unit test `backend/tests/test_command_generator.py`

**Relevant Context**:
- `backend/app/providers/base.py` — `LLMProvider.generate_structured()` interface
- `backend/app/providers/factory.py` — `get_provider()` singleton getter
- Dev environment is Windows (PowerShell) per workspace info
- The `extracted_facts` in state contain `tech_stack` section — use this to generate targeted commands

**Status**: `[ ] pending`

---

## Sub-Task 3b: Tool Registry (`tools.py`)

**Intent**: Define all assistant capabilities as LangChain `@tool` decorated functions in a single registry file. This is the only place capabilities are declared. V1 tools are fully implemented. V2 tools are declared as stubs so the LLM's tool descriptions prepare it for future capabilities without breaking current operation. The tool functions contain zero LangChain-specific internals — they are plain async Python that delegate to the existing modules.

**Expected Outcomes**:
- `backend/assistance/app/tools.py` exists
- `ALL_TOOLS: List[BaseTool]` exported — consumed by `react_agent.py`
- V1 tools fully implemented: `search_state`, `search_qdrant`, `generate_command`, `ingest_context`, `fetch_workflow_state`
- V2 tools declared as stubs: `search_web`, `run_in_sandbox`, `fetch_url` — raise `NotImplementedError` with clear message
- Each `@tool` has a precise docstring — the LLM uses the docstring to decide when to call the tool
- Unit test `test_tools.py` verifies each V1 tool returns the expected output shape
- Swapping to LangGraph `ToolNode` requires zero changes to this file

**Todo List**:
1. Create `backend/assistance/app/tools.py`:
   - Import `context_retriever`, `command_generator` modules (Sub-Tasks 2 + 3)
   - Implement V1 tools using `@tool` decorator:
     ```python
     @tool
     def search_state(query: str) -> str:
         """Search the extracted facts, evidence map, intake draft, and validation
         results from the current workflow state. Use this first for any question
         about the application being migrated."""
         return context_retriever.search_state_sync(query, project_id)

     @tool
     def search_qdrant(query: str) -> str:
         """Semantic search over project documents uploaded by the user.
         Use when search_state returns insufficient results."""
         return context_retriever.search_qdrant_sync(query, project_id)

     @tool
     def generate_command(question: str, missing_reason: str) -> str:
         """Generate a PowerShell or Maven diagnostic command the user can run
         locally to provide the missing context. Use when search_state and
         search_qdrant both return insufficient results."""
         return command_generator.generate_sync(question, missing_reason)

     @tool
     def ingest_context(text: str, context_type: str) -> str:
         """Store text (e.g. command output pasted by the user) into the project
         document collection so future searches can find it."""
         return context_retriever.ingest_text_sync(text, context_type)

     @tool
     def fetch_workflow_state(project_id: str) -> str:
         """Fetch the full current workflow state including all extracted facts,
         confidence scores, intake draft, and validation results."""
         # HTTP GET to main backend — no Python import
         import httpx
         r = httpx.get(f"http://localhost:8000/api/orchestration/state/{project_id}")
         return r.text
     ```
   - Implement V2 stubs:
     ```python
     @tool
     def search_web(query: str) -> str:
         """Search the web for the latest migration documentation, CVEs, framework
         changelogs, or authoritative technical knowledge. (V2 — not yet enabled)"""
         raise NotImplementedError("V2 — search_web not yet implemented")

     @tool
     def run_in_sandbox(code: str, language: str = "python") -> str:
         """Execute a code snippet in an isolated sandbox and return stdout + stderr.
         Use to analyse application code or test migration scripts. (V2 — not yet enabled)"""
         raise NotImplementedError("V2 — run_in_sandbox not yet implemented")

     @tool
     def fetch_url(url: str) -> str:
         """Fetch a URL (official docs page, RFC, release notes) and return
         the cleaned text content. (V2 — not yet enabled)"""
         raise NotImplementedError("V2 — fetch_url not yet implemented")
     ```
   - Export: `ALL_TOOLS = [search_state, search_qdrant, generate_command, ingest_context, fetch_workflow_state, search_web, run_in_sandbox, fetch_url]`
2. Note: LangChain `AgentExecutor` will only call a tool if it doesn't raise — V2 stubs will surface as an Observation telling the LLM "this capability is not yet enabled"
3. Write unit test `backend/assistance/tests/test_tools.py`

**Relevant Context**:
- LangChain `@tool` decorator from `langchain.tools` — already in `requirements.txt` via `langchain==0.1.4`
- `context_retriever.py` (Sub-Task 2) and `command_generator.py` (Sub-Task 3) provide the implementations
- The docstring of each tool IS the tool description the LLM reads — write it carefully
- `fetch_workflow_state` uses `httpx` (already in `requirements.txt`) — not a Python import from main

**Status**: `[ ] pending`

---

## Sub-Task 4: ReAct Agent (`react_agent.py`) — The Swap Point

**Intent**: Build the agent loop in `react_agent.py` using LangChain `AgentExecutor`. This file is explicitly designed to be the **single swap point** when migrating to LangGraph `ToolNode` — every other file (tools, prompts, API, frontend) remains unchanged. It wires the LLM, tool registry, ReAct prompt, and conversation memory together and exposes an `ask_stream()` async generator that yields `AssistantStreamEvent` objects.

**Expected Outcomes**:
- `backend/assistance/app/react_agent.py` exists
- `AgentExecutor` wired with: LangChain-compatible LLM wrapper, `ALL_TOOLS` from `tools.py`, ReAct prompt from `prompts.py`, `ConversationBufferMemory` seeded from `ConversationStore`
- `async def ask_stream(question, project_id) -> AsyncGenerator[AssistantStreamEvent]` — streams each Thought/Action/Observation as an SSE event
- `AssistantStreamEvent` Pydantic model: `event_type: Literal["thought", "action", "observation", "answer_chunk", "command_request", "done"]`, `data: Dict`
- Swap comment block at top of file documents the exact LangGraph replacement code
- LangGraph swap requires changing ~5 lines in this file only
- Unit test covers: single-tool answer, multi-tool answer, V2 stub gracefully handled

**Todo List**:
1. Create `backend/assistance/app/react_agent.py`:
   - Import `ALL_TOOLS` from `tools.py`
   - Import `REACT_SYSTEM_PROMPT` from `prompts.py`
   - Wrap the existing `LLMProvider` (from main backend, via HTTP or own instance) in a LangChain-compatible `BaseLLM` adapter — OR use `langchain_openai.ChatOpenAI` / `langchain_google_genai.ChatGoogleGenerativeAI` directly (own config, own API key)
   - Build `AgentExecutor`:
     ```python
     from langchain.agents import AgentExecutor, create_react_agent
     from langchain.memory import ConversationBufferMemory
     from .tools import ALL_TOOLS
     from .prompts import REACT_SYSTEM_PROMPT

     # Seed memory from ConversationStore (Redis)
     history = await conversation_store.get_history(project_id)
     memory = ConversationBufferMemory(memory_key="chat_history")
     for msg in history[-10:]:   # last 10 turns
         memory.chat_memory.add_user_message(msg["content"] if msg["role"]=="user" else "")
         memory.chat_memory.add_ai_message(msg["content"] if msg["role"]=="assistant" else "")

     agent = create_react_agent(llm, ALL_TOOLS, REACT_SYSTEM_PROMPT)
     executor = AgentExecutor(agent=agent, tools=ALL_TOOLS, memory=memory,
                              verbose=True, handle_parsing_errors=True, max_iterations=8)
     ```
   - `ask_stream()` uses `executor.astream()` or `executor.astream_events()` to capture intermediate steps:
     - Each `"on_tool_start"` event → yield `AssistantStreamEvent(event_type="action", data={tool, input})`
     - Each `"on_tool_end"` event → yield `AssistantStreamEvent(event_type="observation", data={tool, output})`
     - Each `"on_llm_stream"` event → yield `AssistantStreamEvent(event_type="thought", data={chunk})`
     - Final answer → yield `AssistantStreamEvent(event_type="answer_chunk", data={text})` then `done`
   - Persist completed exchange to `ConversationStore` after `done` event
   - Add swap comment block at top of file:
     ```python
     # ── SWAP POINT: LangChain → LangGraph ──────────────────────────────
     # To swap to LangGraph ToolNode, replace the AgentExecutor block with:
     #
     #   from langgraph.prebuilt import create_react_agent   # LangGraph version
     #   executor = create_react_agent(llm, ALL_TOOLS)
     #
     # tools.py, prompts.py, chat.py, and all frontend code are UNCHANGED.
     # ───────────────────────────────────────────────────────────────────
     ```
2. Create `backend/assistance/app/prompts.py`:
   - `REACT_SYSTEM_PROMPT` — ReAct-format prompt:
     - Role: "You are a senior migration architect assistant. You help developers review AI-generated migration intake documents."
     - Tool use instruction: "Use tools to find information before answering. Always check search_state first, then search_qdrant. If both are insufficient, use generate_command and tell the user to run it."
     - Format: `Answer the following questions as best you can. You have access to the following tools:\n{tools}\n\nUse the following format:\nQuestion: ...\nThought: ...\nAction: ...\nAction Input: ...\nObservation: ...\n...(repeat as needed)\nFinal Answer: ...`
   - `build_tool_context(project_id, state_summary)` — builds the per-request context injected before the question (project ID, facts count, phase, top-level facts summary)
3. Write unit test `backend/assistance/tests/test_react_agent.py`

**Relevant Context**:
- `langchain.agents.create_react_agent` + `AgentExecutor` — available in `langchain==0.1.4` already in requirements
- `langchain.agents.AgentExecutor.astream_events()` — streams intermediate steps (LangChain v0.1+)
- `langgraph.prebuilt.create_react_agent` — the future swap; identical tool interface
- The `handle_parsing_errors=True` flag on `AgentExecutor` is critical — LLMs sometimes produce malformed ReAct output; this recovers gracefully instead of crashing
- `max_iterations=8` prevents runaway loops (equivalent to LangGraph's `recursion_limit`)

**Status**: `[ ] pending`
- The `extracted_facts` structure has sections: `tech_stack`, `infrastructure`, `dependencies`, `security`, `deployment` — reference these in prompts
- The `evidence_map` links fact field names to source document references — use for citations

**Status**: `[ ] pending`

---

## Sub-Task 5: Context Ingestion Endpoint (User-Provided Context)

**Intent**: When the user pastes command output or uploads a file, it must be ingested into the existing Qdrant collection (`project_{project_id}`) tagged as `source: "user_assistance"` so ALL future questions in that session benefit. This reuses the exact same chunking + embedding + Qdrant pipeline already used for document uploads.

**Expected Outcomes**:
- `POST /api/assistance/{project_id}/context` endpoint — accepts text paste OR file upload
- Text paste path: chunk the text, embed, store in Qdrant tagged `{"source": "user_assistance", "context_type": "command_output", "added_at": ISO}`
- File upload path: parse via existing `ParserFactory`, chunk, embed, store in Qdrant with same tags
- Returns `ContextIngestionResponse` with `chunks_added`, `collection`, `source_type`
- The assistant's Qdrant search will naturally find these new chunks on the next question
- Unit test: ingest sample text → verify it appears in Qdrant search

**Todo List**:
1. Add to `backend/app/api/assistance.py`:
   - `POST /api/assistance/{project_id}/context` accepting:
     - `text_content: Optional[str]` (for pasted command output)
     - `file: Optional[UploadFile]` (for file upload)
     - `context_type: str` (e.g. "dependency_tree", "project_structure", "java_class")
     - `description: str` (human-readable label)
   - Text path: use existing `DocumentChunker.chunk_text()` → `EmbeddingGenerator.embed_chunks()` → `QdrantStore.add_documents()`
   - File path: use existing `ParserFactory.parse_file()` → chunk → embed → store
   - Tag all documents with `metadata.source = "user_assistance"` and `metadata.project_id = project_id`
   - Return `ContextIngestionResponse`: `chunks_added: int`, `collection: str`, `source_type: str`, `description: str`
2. Do NOT create new Qdrant collections — add to existing `project_{project_id}` collection
3. Reuse these exact existing classes: `ParserFactory` from `backend/app/parsers/parser_factory.py`, `DocumentChunker` from `backend/app/embeddings/chunker.py`, `EmbeddingGenerator` from `backend/app/embeddings/embedder.py`, `QdrantStore` from `backend/app/storage/qdrant_store.py`
4. Write unit test `backend/tests/test_assistance_ingestion.py`

**Relevant Context**:
- `backend/app/api/documents.py` — existing document upload endpoint uses same pattern; follow it exactly
- `backend/app/parsers/parser_factory.py` — `ParserFactory.parse_file(file_path, filename)` returns `{'content': str, 'metadata': dict}`
- `backend/app/embeddings/chunker.py` — `DocumentChunker.chunk_text(text, metadata)` returns `List[Dict]`
- `backend/app/embeddings/embedder.py` — `EmbeddingGenerator.embed_chunks(chunks)` returns chunks with `embedding` field added
- `backend/app/storage/qdrant_store.py` — `add_documents(documents, collection_name)` — documents must have `text`, `embedding`, `metadata`
- Collection name convention: `project_{project_id}` — MUST be consistent

**Status**: `[ ] pending`

---

## Sub-Task 6: API Router (`/api/assistance`)

**Intent**: Wire all assistance modules into a FastAPI router that the existing `main.py` can mount. Two main endpoints: `POST /chat` (streaming SSE response) and `POST /context` (ingestion). The router is the SOA boundary — it owns request/response models and error handling.

**Expected Outcomes**:
- `backend/app/api/assistance.py` with all routes under prefix `/api/assistance`
- `POST /api/assistance/{project_id}/chat` — accepts question, returns SSE stream of `AssistantStreamEvent`
- `POST /api/assistance/{project_id}/context` — accepts text or file, returns ingestion result
- `GET /api/assistance/{project_id}/history` — returns full conversation history
- `DELETE /api/assistance/{project_id}/history` — clears conversation history
- `GET /api/assistance/{project_id}/context` — lists all user-provided context documents in Qdrant
- Mounted in `backend/app/main.py` with zero changes to existing routers
- All errors return consistent `AssistanceErrorResponse` with `error_code`, `message`, `suggestion`

**Todo List**:
1. Create `backend/app/api/assistance.py`:
   - `POST /{project_id}/chat`:
     - Request: `AssistanceChatRequest(question: str)`
     - Returns: `StreamingResponse` (SSE) streaming `AssistantStreamEvent` JSON objects
     - Gets state via `state_manager.get_state(project_id)` — validates it is at `HUMAN_REVIEW` phase
     - Calls `assistant_agent.ask_stream(question, project_id, state)`
     - Each yielded event serialized as `data: {json}\n\n`
   - `POST /{project_id}/context` — from Sub-Task 5
   - `GET /{project_id}/history` — returns `ConversationHistory(project_id, messages: List[ConversationMessage])`
   - `DELETE /{project_id}/history` — clears Redis key, returns `{"cleared": true}`
   - `GET /{project_id}/context` — lists Qdrant docs with `metadata.source == "user_assistance"`
2. Add dependency injection for `AssistantAgent`, `ConversationStore`, `QdrantStore`, `StateManager` using FastAPI `Depends()`
3. Register router in `backend/app/main.py`:
   - `from app.api.assistance import router as assistance_router`
   - `app.include_router(assistance_router, prefix="/api/assistance", tags=["assistance"])`
   - Add this AFTER existing router registrations — no changes to existing routers
4. Add `cors_origins` to cover the new endpoint (already set globally in main.py — no change needed)
5. Write integration test `backend/tests/test_assistance_api.py`

**Relevant Context**:
- `backend/app/main.py` — existing router registration pattern (lines 40-80); follow same pattern for `assistance_router`
- `backend/app/api/orchestration.py` — SSE streaming pattern at `GET /stream/{project_id}` — follow this exact pattern for the chat SSE
- `backend/app/orchestration/state_manager.py` — `get_state(project_id)` used to validate project is at HUMAN_REVIEW
- FastAPI `Depends()` injection pattern — follow same as `backend/app/api/documents.py`

**Status**: `[ ] pending`

---

## Sub-Task 7: Frontend — Advanced Assistance Panel

**Intent**: Add a new "Advanced Assistance" tab to the existing `HumanReview.jsx` page. The tab contains a chat interface with streaming CoT trace display, a file upload zone for context injection, and a "command output" paste area. Uses IBM Carbon Design System components exclusively.

**Expected Outcomes**:
- New "Advanced Assistance" tab in `HumanReview.jsx` (4th tab, after Review Flags / Intake Draft / Validation)
- Chat history renders in a scrollable panel with IBM Carbon styling
- Each assistant message has a collapsible "Thinking trace" section showing CoT steps
- Thinking steps show icon per action: 🔍 CHECK_STATE, 🗄️ SEARCH_QDRANT, ⚡ REQUEST_CONTEXT, ✅ ANSWER
- When assistant returns `needs_more_context: true`, a formatted command block is shown with Copy button
- A text area below the command block allows the user to paste the output and submit it
- File upload drop zone (IBM Carbon `FileUploader`) sends to `POST /api/assistance/{project_id}/context`
- Input bar at the bottom: text field + Send button (disabled during streaming)
- Context panel on the right: list of user-provided context documents already ingested
- IBM Carbon explicit colors: `#161616` text, `#0f62fe` blue, `#ffffff` backgrounds (per CODING_STANDARDS.md rule)

**Todo List**:
1. Create `frontend/src/services/assistanceApi.js`:
   - `sendMessage(projectId, question)` → returns `EventSource` connected to `POST /api/assistance/{projectId}/chat` via streaming
   - `uploadContext(projectId, formData)` → `POST /api/assistance/{projectId}/context`
   - `getHistory(projectId)` → `GET /api/assistance/{projectId}/history`
   - `clearHistory(projectId)` → `DELETE /api/assistance/{projectId}/history`
   - `getContextDocuments(projectId)` → `GET /api/assistance/{projectId}/context`
2. Create `frontend/src/hooks/useAssistance.js`:
   - State: `messages`, `isStreaming`, `currentThinkingSteps`, `error`
   - `sendMessage(question)` — opens SSE, appends thinking steps in real-time, finalizes message
   - `submitCommandOutput(output, contextType)` — calls uploadContext with text
   - `uploadFile(file, contextType)` — calls uploadContext with file
3. Create `frontend/src/components/AssistancePanel.jsx`:
   - Renders the full chat interface using IBM Carbon components
   - `ChatMessage` sub-component: shows role indicator, content, collapsible ThinkingTrace
   - `ThinkingTrace` sub-component: ordered list of steps with icons and confidence badges
   - `CommandBlock` sub-component: formatted `<code>` block with IBM Carbon `CopyButton` + output paste area
   - `ContextList` sub-component: shows ingested context docs with filename/type/date
   - `FileDropZone` sub-component: IBM Carbon `FileUploader` wired to uploadContext
4. Update `frontend/src/pages/HumanReview.jsx`:
   - Import `AssistancePanel`
   - Add 4th `Tab` to the Carbon `Tabs` component: `<Tab label="Advanced Assistance" />`
   - Render `<AssistancePanel projectId={projectId} />` inside the new `TabPanel`
   - No changes to any of the existing 3 tabs
5. Create `frontend/src/pages/HumanReview.scss` additions (or new `AssistancePanel.scss`):
   - `.chat-container` — scrollable with max-height
   - `.thinking-trace` — indented, monospace, light gray background `#f4f4f4`
   - `.command-block` — dark terminal style `#161616` bg, `#42be65` green text
   - `.user-message` / `.assistant-message` — left/right alignment
   - `.confidence-badge` — color-coded: `#24a148` high, `#f1c21b` medium, `#da1e28` low

**Relevant Context**:
- `frontend/src/pages/HumanReview.jsx` — existing tab structure (Carbon `Tabs`, `Tab`, `TabPanel`); add 4th tab at line ~223
- `frontend/src/hooks/useWorkflowSSE.js` — SSE pattern to follow for streaming
- `frontend/src/services/api.js` — existing API client pattern
- `frontend/src/components/IntakeDraftViewer.jsx` — Carbon component pattern to follow for new components
- IBM Carbon Design System explicit color rule: **always** use `#161616` for text, `#0f62fe` for interactive blue, never rely on defaults (per `.agents/CODING_STANDARDS.md`)

**Status**: `[ ] pending`

---

## Sub-Task 8: Prompt Engineering & CoT Testing

**Intent**: Design and validate the system prompts and CoT reasoning prompts for the Assistant Agent. This is a separate sub-task because prompt quality directly determines answer quality — it needs dedicated testing, iteration, and documentation.

**Expected Outcomes**:
- `backend/app/assistance/prompts.py` is finalized with tested prompts
- At least 5 representative test scenarios are validated manually:
  1. Question answerable from `extracted_facts` (state only)
  2. Question answerable from Qdrant but not in state
  3. Question requiring Maven dependency tree command
  4. Question requiring project structure command
  5. Question after user pastes command output (verifies ingested context is used)
- Prompt testing script `backend/poc/test_assistance_prompts.py` that runs all 5 scenarios against real LLM
- Results documented in `docs/ASSISTANCE_PROMPT_TESTING.md`

**Todo List**:
1. `REACT_SYSTEM_PROMPT` is already defined in Sub-Task 4 (`prompts.py`). This sub-task finalises and tests it.
2. Test all 5 scenarios:
   - Scenario 1: Question answerable from `extracted_facts` → verify `search_state` called once, `final_answer` immediate
   - Scenario 2: Question answerable from Qdrant only → verify `search_state` then `search_qdrant` called
   - Scenario 3: Both insufficient → verify `generate_command` called, `needs_more_context=True` returned
   - Scenario 4: After user pastes output → verify `ingest_context` called, follow-up uses new chunks
   - Scenario 5: V2 stub called by LLM → verify graceful Observation "V2 not yet enabled", agent continues
3. Create `backend/assistance/poc/test_react_prompts.py` — runs 5 scenarios with real LLM
4. Document tool docstring iterations in `docs/ASSISTANCE_PROMPT_TESTING.md`
5. Verify `max_iterations=8` is sufficient for the most complex scenario (Scenario 3 typically needs 4–6 turns)

**Relevant Context**:
- `docs/12-agent-orchestration-analysis.md` — persona-driven prompt style to follow
- `.agents/CODING_STANDARDS.md` — agent prompt standards
- ReAct prompt format: `{tools}`, `{tool_names}`, `{agent_scratchpad}`, `{input}` are the 4 required variables
- Tool docstrings ARE the tool descriptions — every word counts for LLM tool selection accuracy

**Status**: `[ ] pending`

---

## Sub-Task 9: Integration Testing & Documentation

**Intent**: Verify the full end-to-end flow works: workflow reaches Human Review → user opens Assistance tab → asks a question → CoT trace shows → context is added → follow-up question uses the new context. Also update all agent memory files.

**Expected Outcomes**:
- Full integration test passes: workflow to Human Review → 3 assistance questions → context ingestion → follow-up answer uses ingested context
- `docs/ADVANCED_ASSISTANCE_PLAN.md` (this file) sub-task statuses updated to `[x] done`
- `.agents/ARCHITECTURE_PATTERNS.md` updated with "Pattern 10: Advanced Assistance CoT Pattern"
- `.agents/CODING_STANDARDS.md` updated with `AssistancePanel.scss` color standard
- `.agents/CRITICAL_BUGS_MEMORY.md` updated with any new critical patterns discovered
- `README.md` updated with new service section

**Todo List**:
1. Write integration test `backend/assistance/tests/test_assistance_integration.py`:
   - Setup: start both services (main `:8000` + assistance `:8001`); init workflow to HUMAN_REVIEW
   - Test 1: QUERY `/chat/{project_id}` → stream events → verify `thought`, `action`, `observation`, `done` all present
   - Test 2: POST `/context/{project_id}` with text → verify Qdrant has new doc tagged `user_assistance`
   - Test 3: Follow-up QUERY → verify `search_qdrant` action is called and references ingested chunk
   - Test 4: GET `/history/{project_id}` → verify 2 exchanges stored with Thought/Action/Obs trace
   - Test 5: V2 stub scenario → verify stream completes with graceful message (no 500 error)
2. Update `.agents/ARCHITECTURE_PATTERNS.md` — add Pattern 10: ReAct Assistance Pattern (tool registry, swap point, V1/V2 stub pattern)
3. Update README.md — verified already updated; confirm no drift
4. Run full test suite on both services; verify no regressions in existing main backend tests

**Relevant Context**:
- `.agents/ARCHITECTURE_PATTERNS.md` — 9 existing patterns; new pattern follows same format
- `backend/tests/test_orchestration.py` — integration test pattern to follow
- `.agents/CRITICAL_BUGS_MEMORY.md` — pre-commit checklist; verify all items pass before committing

**Status**: `[ ] pending`

---

## Implementation Order

```
Sub-Task 1: ConversationStore         ← Foundation (Redis, standalone service)
     ↓
Sub-Task 2: ContextRetriever          ← search_state + search_qdrant implementations
     ↓
Sub-Task 3: CommandGenerator          ← generate_command implementation
     ↓
Sub-Task 3b: Tool Registry (tools.py) ← @tool wrappers + V2 stubs (depends on 2,3)
     ↓
Sub-Task 4: ReAct Agent (react_agent.py) ← AgentExecutor + streaming (depends on 3b)
     ↓
Sub-Task 5: Ingestion Endpoint        ← POST /context (parallel with 4)
     ↓
Sub-Task 6: Standalone FastAPI app    ← main.py :8001 + Dockerfile + podman-compose
     ↓
Sub-Task 7: Frontend Panel            ← AssistancePanel.jsx + streamChat helper
     ↓
Sub-Task 8: Prompt Engineering        ← Tool docstrings + ReAct prompt testing (5 scenarios)
     ↓
Sub-Task 9: Integration Testing       ← End-to-end across both services
```

---

## New Files to Create

```
backend/assistance/                    ← NEW standalone SOA service
├── app/
│   ├── main.py                        (Sub-Task 6) ← FastAPI :8001
│   ├── api/
│   │   ├── chat.py                    (Sub-Task 6) ← QUERY endpoint
│   │   ├── context.py                 (Sub-Task 5)
│   │   └── history.py                 (Sub-Task 6)
│   ├── react_agent.py                 (Sub-Task 4) ← SWAP POINT
│   ├── tools.py                       (Sub-Task 3b) ← @tool registry
│   ├── context_retriever.py           (Sub-Task 2)
│   ├── command_generator.py           (Sub-Task 3)
│   ├── conversation_store.py          (Sub-Task 1)
│   └── prompts.py                     (Sub-Task 4 + 8)
├── tests/
│   ├── test_conversation_store.py     (Sub-Task 1)
│   ├── test_context_retriever.py      (Sub-Task 2)
│   ├── test_command_generator.py      (Sub-Task 3)
│   ├── test_tools.py                  (Sub-Task 3b)
│   ├── test_react_agent.py            (Sub-Task 4)
│   ├── test_ingestion.py              (Sub-Task 5)
│   ├── test_api.py                    (Sub-Task 6)
│   └── test_assistance_integration.py (Sub-Task 9)
├── poc/
│   └── test_react_prompts.py          (Sub-Task 8)
├── requirements.txt                   (Sub-Task 6)
└── Dockerfile                         (Sub-Task 6)

frontend/src/services/
└── assistanceApi.js                   (Sub-Task 7)

frontend/src/hooks/
└── useAssistance.js                   (Sub-Task 7)

frontend/src/components/
└── AssistancePanel.jsx                (Sub-Task 7)

docs/
└── ASSISTANCE_PROMPT_TESTING.md       (Sub-Task 8)
```

## Files Modified (Surgical Changes Only)

```
frontend/src/pages/HumanReview.jsx  ← Add 4th tab (5-10 lines)
frontend/vite.config.js             ← Add /api/assistance proxy rule (2 lines)
podman-compose.yml                  ← Add assistance service container (Sub-Task 6)
.agents/ARCHITECTURE_PATTERNS.md   ← Add Pattern 10: ReAct Assistance (Sub-Task 9)
```

Note: `backend/app/main.py` is **NOT modified** — the assistance service is fully standalone.

---

## Pre-Commit Checklist (Additions to Standard Checklist)

```
- [ ] All new assistance endpoints validate project is at HUMAN_REVIEW phase
- [ ] Qdrant collection name always uses project_{project_id} — never hardcoded
- [ ] Conversation history key always uses assistance:{project_id}:history — never collides with state:{project_id}
- [ ] No Python imports from backend/app/ inside backend/assistance/ — SOA boundary enforced
- [ ] fetch_workflow_state tool uses httpx HTTP call, never a Python import
- [ ] All LLM calls use own provider instance (langchain_openai / langchain_google_genai) — not main backend factory
- [ ] AgentExecutor has handle_parsing_errors=True and max_iterations=8 — never omit these
- [ ] ALL @tool functions have precise docstrings — the LLM uses them for tool selection
- [ ] V2 stub tools raise NotImplementedError — never silently return empty string
- [ ] react_agent.py has the SWAP POINT comment block at the top — never remove it
- [ ] ThinkingStep/event timestamps use datetime.utcnow().isoformat() — Critical Rule #1
- [ ] All new Pydantic models initialized with all fields — Critical Rule #2
- [ ] IBM Carbon explicit colors in all new SCSS — Critical Rule #5
```

---

**Plan Written By**: Bob (AI Planning Agent)
**Based On**: Full codebase analysis + 6 user clarification rounds including ReAct framework decision
**Reasoning engine decision**: LangChain AgentExecutor (V1) → LangGraph ToolNode (V2) — swap point isolated in react_agent.py
**Status**: Updated with ReAct framework — ready for implementation
