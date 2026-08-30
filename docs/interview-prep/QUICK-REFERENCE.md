# Quick Reference Card — 5 YOE Patterns

**One-page cheat sheet for interviews and whiteboarding**

---

## Pattern 1: Optimistic Locking for State Management

```python
# Problem: Concurrent updates lose data
# Solution: Version checking at commit time

class StateManager:
    async def commit_state(self, project_id, patch):
        # NOTE: asyncio.Lock is single-process only.
        # In a multi-pod/multi-worker deployment you need a
        # distributed lock (e.g. Redis SETNX with expiry).
        # See "Production Note" below.
        async with self._lock:
            # Step 1: Read current state
            current = await self.redis.get(f"state:{project_id}")
            read_version = current['state_version']

            # Step 2: Validate patch (reject protected fields)
            self._validate_patch(patch)

            # Step 3: Re-read version from store to detect concurrent writes
            # (Do NOT compare read_version to itself — they are always equal.
            #  Re-fetch from Redis so another writer's update is visible.)
            fresh = await self.redis.get(f"state:{project_id}")
            if fresh['state_version'] != read_version:
                raise StateTransactionError("Version mismatch — retry")

            # Step 4: Build and atomically write new state
            new_state = {
                **fresh,
                **patch,
                'state_version': read_version + 1,
                'state_changelog': [*fresh['state_changelog'], new_entry]
            }
            await self.redis.set(f"state:{project_id}", new_state)
            return new_state

# ⚠️ Production Note — distributed lock for multi-pod deployments:
# async def acquire_lock(redis, project_id, ttl=10):
#     key = f"lock:{project_id}"
#     return await redis.set(key, "1", nx=True, ex=ttl)  # SETNX + EXPIRY
# Prevents one process from holding the lock forever if it crashes.

# Conflict resolution: Agent retries with refreshed state
try:
    await manager.commit_state(project_id, my_patch)
except StateTransactionError:
    # Retry: re-read latest state, recompute patch if needed
    current = await manager.get_state(project_id)
    await manager.commit_state(project_id, recompute_patch(current))
```

**📂 See actual code:**
- State schema: [`backend/app/orchestration/state.py` (L82-150)](../../backend/app/orchestration/state.py)
- State manager: [`backend/app/orchestration/state_manager.py` (L120-250)](../../backend/app/orchestration/state_manager.py)
- Exception types: [`backend/app/orchestration/state_manager.py` (L27-35)](../../backend/app/orchestration/state_manager.py)

**Interview tip:** "Optimistic locking: detect conflict at write time, not read time. `asyncio.Lock` is single-process — add Redis SETNX for multi-pod."

---

## Pattern 2: Circuit Breaker for Resilience

```python
# Problem: Dead service crashes everything
# Solution: Fast-fail and fall back

class ProviderFactory:
    async def get_provider(self):
        # Try primary if healthy
        if self.primary_status == ProviderStatus.HEALTHY:
            return self.primary_provider
        
        # Try fallback
        if self.fallback_status == ProviderStatus.HEALTHY:
            logger.info("Using fallback provider")
            return self.fallback_provider
        
        raise RuntimeError("No providers available")
    
    async def handle_failure(self, provider):
        self.failure_count += 1
        if self.failure_count >= 3:  # Circuit opens
            if provider == self.primary_provider:
                self.primary_status = ProviderStatus.UNAVAILABLE
            else:
                self.fallback_status = ProviderStatus.UNAVAILABLE
        else:
            # CORRECT: status lives on the factory, not the provider instance
            if provider == self.primary_provider:
                self.primary_status = ProviderStatus.DEGRADED
            else:
                self.fallback_status = ProviderStatus.DEGRADED

    async def handle_success(self, provider):
        self.failure_count = 0  # Reset on success
        # Reset the factory-level status, not provider instance attribute
        if provider == self.primary_provider:
            self.primary_status = ProviderStatus.HEALTHY
        else:
            self.fallback_status = ProviderStatus.HEALTHY

# State transitions:
# HEALTHY ─(failure)─> DEGRADED ─(max_failures=3)─> UNAVAILABLE
#                                                            │
#                     (success resets counter) <─────────────┘
```

**📂 See actual code:**
- Factory + circuit breaker: [`backend/app/providers/factory.py` (L26-150)](../../backend/app/providers/factory.py)
- Status enum: [`backend/app/providers/factory.py` (L19-23)](../../backend/app/providers/factory.py)
- Abstract interface: [`backend/app/providers/base.py` (L37-140)](../../backend/app/providers/base.py)

**Interview tip:** "Circuit breaker has 3 states. Prevents hammering dead service."

---

## Pattern 3: LangGraph with Supervisor Routing

```python
# Problem: Orchestrate multi-agent workflow with pauses
# Solution: Supervisor routes based on state

graph = StateGraph(MigrationState)

# Add agent nodes
graph.add_node("extraction_agent", _extraction_node)
graph.add_node("questionnaire_agent", _questionnaire_node)
graph.add_node("supervisor", _supervisor_node)

# Agents report to supervisor
graph.add_edge("extraction_agent", "supervisor")
graph.add_edge("questionnaire_agent", "supervisor")

# Supervisor routes to next
graph.add_conditional_edges(
    "supervisor",
    decide_next_node,
    {
        "extraction_agent": "extraction_agent",
        "questionnaire_agent": "questionnaire_agent",
        "END": END
    }
)

async def decide_next_node(state):
    if state['phase'] == WorkflowPhase.EXTRACTION:
        return "questionnaire_agent"
    elif state['phase'] == WorkflowPhase.QUESTIONNAIRE:
        return "intake_draft_agent"
    elif state['phase'] == WorkflowPhase.INTAKE_DRAFT:
        # ✓ Pause for human review
        if not state['human_reviewed']:
            return "END"  # Pause here
        else:
            return "migration_planning_agent"  # Resume here
    return "END"

# GOTCHA: Don't return "human_review" node (infinite loop)
```

**See actual code:**
- Workflow: [`backend/app/orchestration/workflow.py` (L28-100, L100-200)](../../backend/app/orchestration/workflow.py)
- Supervisor: [`backend/app/orchestration/supervisor.py` (L80-150)](../../backend/app/orchestration/supervisor.py)

**Interview tip:** "Return 'END' to pause, not recursion. Frontend resumes via API."

---

## Pattern 4: Annotated Reducers for State Merging

```python
# Problem: How do concurrent agent updates merge?
# Solution: Custom reducers define merge behavior

def merge_lists(left, right):
    """Append right to left"""
    if not left: left = []
    if not right: right = []
    return left + right

def merge_dicts(left, right):
    """Shallow merge, right takes precedence"""
    if not left: left = {}
    if not right: right = {}
    return {**left, **right}

class MigrationState(TypedDict):
    # Lists accumulate (agents append)
    normalized_docs: Annotated[List[Dict], merge_lists]
    missing_questions: Annotated[List[Dict], merge_lists]
    
    # Dicts merge (new keys added, existing updated)
    trace_metadata: Annotated[Dict[str, Any], merge_dicts]

# Example merge:
# Agent 1 patch: {normalized_docs: [{id: 2}], trace_metadata: {extraction: {...}}}
# Agent 2 patch: {normalized_docs: [{id: 3}], trace_metadata: {questionnaire: {...}}}
# Result: {
#   normalized_docs: [{id: 2}, {id: 3}],  # Concatenated!
#   trace_metadata: {extraction: {...}, questionnaire: {...}}  # Merged!
# }
```

**📂 See actual code:**
- Reducers: [`backend/app/orchestration/state.py` (L14-46)](../../backend/app/orchestration/state.py)
- State fields using reducers: [`backend/app/orchestration/state.py` (L110-150)](../../backend/app/orchestration/state.py)

**Interview tip:** "Reducers handle merging transparently. Lists append, dicts merge."

---

## Pattern 5: Error Recovery Layers

```python
# Layer 1: Agent (returns error patch, doesn't throw)
async def extract_facts(state):
    try:
        return await llm.generate_structured(prompt, schema)
    except TimeoutError:
        return {
            'extracted_facts': None,
            'review_flags': ['LLM timeout during extraction']
        }

# Layer 2: Node (catch and log)
async def _extraction_node(state):
    try:
        agent = ExtractionAgent()
        result = await agent.execute(state)
        return result
    except Exception as e:
        logger.error(f"Extraction failed: {e}", exc_info=True)
        return {
            'phase': WorkflowPhase.ERROR,
            'last_error': str(e),
            'retry_count': state['retry_count'] + 1
        }

# Layer 3: Supervisor (check retries)
async def decide_next_node(state):
    if state['phase'] == WorkflowPhase.ERROR:
        if state['retry_count'] < state['max_retries']:
            return "extraction_agent"  # Retry
        else:
            return "END"  # Give up

# Layer 4: API (catch transaction errors)
@app.post("/execute")
async def execute_workflow(project_id: str):
    try:
        await orchestrator.execute_workflow(project_id)
    except StateTransactionError as e:
        # Version conflict: client retries
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        # Internal error
        raise HTTPException(status_code=500, detail=str(e))
```

**📂 See actual code:**
- Layer 1 (agent): [`backend/app/agents/extraction_agent.py`](../../backend/app/agents/extraction_agent.py)
- Layer 2 (node): [`backend/app/orchestration/workflow.py` (L200-300)](../../backend/app/orchestration/workflow.py)
- Layer 3 (supervisor): [`backend/app/orchestration/supervisor.py` (L100-200)](../../backend/app/orchestration/supervisor.py)
- Layer 4 (API): [`backend/app/main.py` (L113-145)](../../backend/app/main.py)

**Interview tip:** "4 layers: agent returns patches, node logs, supervisor retries, API returns HTTP status."

---

## Pattern 6: Retry with Exponential Backoff

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)  # 2s, 4s, 10s
)
async def fetch_from_mcp(profile):
    # Attempt 1: immediate fail → sleep 2-4s
    # Attempt 2: immediate fail → sleep 4-8s
    # Attempt 3: immediate fail → raise
    pass

# Manual backoff:
for attempt in range(max_attempts):
    try:
        result = await risky_operation()
        return result
    except TransientError as e:
        if attempt < max_attempts - 1:
            wait_time = 2 ** attempt + random()  # Exponential
            await asyncio.sleep(wait_time)
        else:
            raise

# When to use: Transient failures (network glitches, temporary overload)
# NOT for: Permanent errors (401, 404, validation errors)
```

**📂 See actual code:**
- MCP connector with tenacity: [`backend/app/mcp/connector.py`](../../backend/app/mcp/connector.py)
- Provider factory retries: [`backend/app/providers/factory.py` (L140-200)](../../backend/app/providers/factory.py)

**Interview tip:** "Exponential backoff: 1s, 2s, 4s, 8s. Allows downstream recovery."

---

## Pattern 7: Dependency Injection with FastAPI

```python
# Problem: Tightly coupled to concrete implementations
# Solution: Inject dependencies

# Define provider
async def get_state_manager() -> StateManager:
    if not hasattr(get_state_manager, 'instance'):
        get_state_manager.instance = StateManager()
    return get_state_manager.instance

# Inject into endpoint
@app.post("/execute")
async def execute_workflow(
    project_id: str,
    manager: Annotated[StateManager, Depends(get_state_manager)]
):
    # manager is injected by FastAPI
    state = await manager.get_state(project_id)
    return {"state": state}

# Benefits:
# - Easy to mock for testing
# - Can swap implementations without changing code
# - Follows Dependency Inversion Principle (SOLID)
```

**📂 See actual code:**
- Lifespan + DI setup: [`backend/app/main.py` (L39-81)](../../backend/app/main.py)
- Config as injectable: [`backend/app/config.py`](../../backend/app/config.py)

**Interview tip:** "Dependency injection decouples from implementations. Easy to test."

---

## Pattern 8: Server-Sent Events (SSE) for Real-Time Updates

```python
# Problem: Frontend needs real-time state updates
# Solution: Server pushes via SSE (not polling)

@app.get("/stream/{project_id}")
async def stream_updates(project_id: str):
    async def event_generator():
        previous_phase = None
        while True:
            state = await state_manager.get_state(project_id)
            
            # Send state update
            yield f"event: state_update\n"
            yield f"data: {json.dumps(state.model_dump())}\n\n"
            
            # Send phase transition
            if state['phase'] != previous_phase:
                yield f"event: phase_transition\n"
                yield f"data: {json.dumps({
                    'from': previous_phase,
                    'to': state['phase']
                })}\n\n"
                previous_phase = state['phase']
            
            # Break on completion
            if state['phase'] == WorkflowPhase.COMPLETE:
                break
            
            await asyncio.sleep(1)
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Frontend
eventSource = new EventSource(`/api/orchestration/stream/${projectId}`)
eventSource.addEventListener('state_update', (e) => {
    const state = JSON.parse(e.data)
    updateUI(state)
})
eventSource.addEventListener('phase_transition', (e) => {
    const {from, to} = JSON.parse(e.data)
    showPhaseChange(from, to)
})
```

**📂 See actual code:**
- Backend SSE endpoint: [`backend/app/api/orchestration.py` (L250-350)](../../backend/app/api/orchestration.py)
- Frontend SSE hook: [`frontend/src/hooks/useWorkflowSSE.js` (L1-176)](../../frontend/src/hooks/useWorkflowSSE.js)

**Interview tip:** "SSE is one-way (server → client), perfect for updates. Fallback to polling."

---

## Trade-offs Decision Table

| Scenario | Choice | Why | Alternative |
|----------|--------|-----|-------------|
| Read-heavy workflow | Optimistic lock | Lock-free reads | Pessimistic: slower |
| Provider selection | Circuit breaker | Prevent cascades | Always retry: bad UX |
| Agent orchestration | LangGraph | Conditional routing | Manual state machine: harder |
| Real-time updates | SSE | Simple, HTTP | WebSocket: bidirectional overhead |
| State merging | Annotated reducers | Transparent merge | Last-write-wins: data loss |
| Error handling | 4-layer approach | Specific recovery | Catch-all: poor debugging |
| Retry | Exponential backoff | Gradual recovery | Linear: same wait times |
| Dependencies | Inject | Testable, flexible | Hardcoded: brittle |

---

## Whiteboard Template

**Question:** "Design workflow orchestration for AI agents"

```
1. PROBLEM
   - Multi-agent system
   - Concurrent updates
   - Need pause/resume
   - Error recovery

2. CONSTRAINTS
   - Throughput: 100 concurrent workflows
   - Latency: < 5s per phase
   - Availability: 99.9%
   - Consistency: strong (no lost updates)

3. HIGH LEVEL
   ┌─────────────┐
   │  FastAPI    │ (Route requests)
   ├─────────────┤
   │ LangGraph   │ (Orchestrate agents)
   ├─────────────┤
   │ State Mgr   │ (Optimistic locking)
   ├─────────────┤
   │ Redis       │ (Cache state)
   └─────────────┘

4. DEEP DIVE: State Management
   - Immutable TypedDict with version
   - Agents propose patches (no direct modification)
   - Commit checks version (optimistic lock)
   - Changelog for audit trail

5. DEEP DIVE: Resilience
   - Provider factory with circuit breaker
   - Retry with exponential backoff
   - 3-layer error recovery
   - Checkpoints for replay

6. SCALE: 1000 concurrent workflows
   - Per-project locks (not global)
   - Redis sharding by project_id % N
   - Parallel independent agent calls
   - MessagePack serialization

7. MONITORING
   - Error rate per phase
   - Retry frequency
   - Phase duration
   - SSE latency
```

---

## Key Numbers to Remember

- **Circuit breaker:** 3 failures → mark UNAVAILABLE
- **Retry backoff:** 2s, 4s, 8s (exponential)
- **Lock timeout:** 10 seconds (prevents deadlock)
- **Redis TTL:** 3600 seconds (1 hour)
- **Checkpoint interval:** Every 5 commits
- **Concurrent workflows target:** 100
- **Max workflow duration:** 30 minutes
- **Version check failure:** Retry up to 3 times

---

## Common Mistakes (Avoid These!)

1. ❌ Holding lock during entire agent processing → Use optimistic lock
2. ❌ No version checking → Lost updates from concurrent agents
3. ❌ Comparing `read_version` to itself → Always equal; re-read from Redis first
4. ❌ Using `asyncio.Lock` in multi-pod deployment → Distribute via Redis SETNX
5. ❌ Setting `provider.status` (instance attr) → Status lives on `ProviderFactory`
6. ❌ Module-level `embeddings_cache = {}` → Unbounded memory leak; use `TTLCache`
7. ❌ Retrying permanent errors (401, 404) → Check error type first
8. ❌ Global lock for all projects → Use per-project locks; use `setdefault` to avoid race
9. ❌ No circuit breaker → Cascading failures when provider down
10. ❌ Returning "human_review" node → Infinite recursion, return "END"
11. ❌ No idempotency → Retries create duplicate records
12. ❌ Polling instead of SSE → Wastes bandwidth, slow updates

---

## ⚠️ POC vs Production: What This Codebase Omits

| Concern | POC (this codebase) | Production add-on |
|---------|--------------------|--------------------|
| **Distributed lock** | `asyncio.Lock` (single-process) | Redis `SETNX` + `EXPIRE` across pods |
| **Per-project lock** | `dict[project_id]` | `WeakValueDictionary` to prevent unbounded growth |
| **Embeddings cache** | Plain `dict` | `cachetools.TTLCache(maxsize=N, ttl=3600)` |
| **Correlation IDs** | None | `X-Request-ID` header propagated through all log lines |
| **Structured logging** | `logging.getLogger` | JSON logs with `trace_id`, `project_id`, `phase` fields |
| **Graceful shutdown** | SIGTERM closes immediately | Drain in-flight requests before exit; drain timeout ~30s |
| **Health checks** | Single `/health` | Separate `/health/live` (no I/O) and `/health/ready` (deep check) |
| **Connection pooling** | New connection per request | Pooled Redis/Qdrant clients at startup (reuse across requests) |
| **JWT validation** | `jwt.decode(token, key)` | + `audience`, `issuer` claims validated |
| **Circuit breaker scope** | In-memory (single process) | Shared state in Redis so all pods see the same status |

**Key interview talking point:** "In production I'd add correlation IDs and structured logs so every log line carries `trace_id` and `project_id`. This turns 'something failed in extraction' into 'extraction failed for project X in trace Y at timestamp Z'."

---

**Made with Bob**
# IMPORTANT: Code References

Each pattern has corresponding code in the actual codebase. Quick links:

- **Pattern 1 (Optimistic Locking):** See `backend/app/orchestration/state.py` (L82-150) and `state_manager.py` (L120-250)
- **Pattern 2 (Circuit Breaker):** See `backend/app/providers/factory.py` (L26-150)
- **Pattern 3 (LangGraph):** See `backend/app/orchestration/workflow.py` (L28-200) and `supervisor.py` (L80-150)
- **Pattern 4 (Annotated Reducers):** See `backend/app/orchestration/state.py` (L14-140)
- **Pattern 5 (Error Recovery):** See `backend/app/main.py` (L113-145)
- **Pattern 6 (Retry & Backoff):** See `backend/app/tracing/langsmith.py`
- **Pattern 7 (Dependency Injection):** See `backend/app/main.py` (L39-81)
- **Pattern 8 (SSE Streaming):** See `backend/app/api/orchestration.py` (L250-350)

👉 See `CODE-REFERENCE.md` for detailed file-by-file navigation

---

