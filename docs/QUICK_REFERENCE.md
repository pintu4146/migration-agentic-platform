# Quick Reference Card — 5 YOE Patterns

**One-page cheat sheet for interviews and whiteboarding**

---

## Pattern 1: Optimistic Locking for State Management

```python
# Problem: Concurrent updates lose data
# Solution: Version checking at commit time

class StateManager:
    async def commit_state(self, project_id, patch):
        async with self._lock:
            current = await self.redis.get(f"state:{project_id}")
            read_version = current['state_version']
            
            # KEY: Check version hasn't changed
            if current['state_version'] != read_version:
                raise StateTransactionError("Version mismatch")
            
            # Write with new version
            new_state = {
                **current,
                **patch,
                'state_version': read_version + 1,
                'state_changelog': [..., new_entry]
            }
            
            await self.redis.set(f"state:{project_id}", new_state)
            return new_state

# Conflict resolution: Agent retries with new version
try:
    await manager.commit_state(project_id, my_patch)
except StateTransactionError:
    # Retry with updated state
    current = await manager.get_state(project_id)
    await manager.commit_state(project_id, {**my_patch, ...updated_data...})
```

**Interview tip:** "Optimistic locking works well when reads >> writes. If conflict rate is high, switch to pessimistic."

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
            provider.status = ProviderStatus.DEGRADED
    
    async def handle_success(self, provider):
        self.failure_count = 0  # Reset on success
        provider.status = ProviderStatus.HEALTHY

# State transitions:
# HEALTHY ─(failure)─> DEGRADED ─(max_failures=3)─> UNAVAILABLE
#                                                            │
#                     (success resets counter) <─────────────┘
```

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
3. ❌ Retrying permanent errors (401, 404) → Check error type first
4. ❌ Global lock for all projects → Use per-project locks
5. ❌ No circuit breaker → Cascading failures when provider down
6. ❌ Returning "human_review" node → Infinite recursion, return "END"
7. ❌ No idempotency → Retries create duplicate records
8. ❌ Polling instead of SSE → Wastes bandwidth, slow updates

---

**Made with Bob**
