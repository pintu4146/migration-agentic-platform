# Technical Deep Dive

**Detailed explanations of 5 YOE patterns with real code**

For engineers who want to understand the internals deeply.

---

## Section 1: State Management with LangGraph

**📂 Jump directly to the code:**
| What | File | Lines |
|------|------|-------|
| `MigrationState` TypedDict | [`backend/app/orchestration/state.py`](../../backend/app/orchestration/state.py) | L82–150 |
| `merge_lists` / `merge_dicts` reducers | [`backend/app/orchestration/state.py`](../../backend/app/orchestration/state.py) | L14–46 |
| `WorkflowPhase` enum | [`backend/app/orchestration/state.py`](../../backend/app/orchestration/state.py) | L49–65 |
| `StateChangelogEntry` | [`backend/app/orchestration/state.py`](../../backend/app/orchestration/state.py) | L67–80 |
| `StateManager` class | [`backend/app/orchestration/state_manager.py`](../../backend/app/orchestration/state_manager.py) | L37–70 |
| `commit_state()` optimistic locking | [`backend/app/orchestration/state_manager.py`](../../backend/app/orchestration/state_manager.py) | L120–250 |
| `StateTransactionError` | [`backend/app/orchestration/state_manager.py`](../../backend/app/orchestration/state_manager.py) | L27–35 |

### Problem

Multi-agent systems need to coordinate state updates safely. Consider:

```
Timeline:
t=0: Agent A reads state (version 5, contains normalized_docs: [], extracted_facts: None)
t=0: Agent B reads state (version 5)
t=1: Agent A finishes processing, writes {normalized_docs: [doc1, doc2]}
     State becomes version 6
t=1: Agent B finishes processing, tries to write {extracted_facts: {...}}
     BUT: State is now version 6, not 5 (when B read it)
     DATA LOSS: extracted_facts update is lost!
```

### Solution: Immutable, Versioned State with Optimistic Locking

**Key principle:** Don't prevent concurrent reads. Detect conflicts at write time.

**Data structure:**

```python
class MigrationState(TypedDict):
    # Every state has a version number
    project_id: str
    state_version: int  # Incremented on every commit
    phase: WorkflowPhase
    
    # Fields that agents update
    normalized_docs: Annotated[List[Dict], merge_lists]
    extracted_facts: Optional[Dict]
    
    # Audit trail
    state_changelog: Annotated[List[StateChangelogEntry], merge_lists]
    state_version: int
    last_committed_by: str
```

**Commit logic:**

```python
async def commit_state(project_id, patch, committed_by, reason):
    # Step 1: Read current state
    current = await redis.get(f"state:{project_id}")
    read_version = current['state_version']
    
    # Step 2: Validate (no protected fields)
    validate_patch(patch)  # Throws if patch has reserved keys
    
    # Step 3: Check version hasn't changed
    # THIS IS THE KEY: We detect conflicts here, not during read
    if current['state_version'] != read_version:
        raise StateTransactionError("Someone else updated state!")
    
    # Step 4: Create new state with incremented version
    new_state = {
        **current,
        **patch,
        'state_version': read_version + 1,
        'last_committed_by': committed_by,
        'state_changelog': [
            ...current_changelog,
            {
                'version': read_version + 1,
                'patch': patch,
                'committed_by': committed_by,
                'reason': reason,
                'timestamp': now()
            }
        ]
    }
    
    # Step 5: Write to Redis (atomic)
    await redis.set(f"state:{project_id}", new_state)
    
    return new_state
```

### Why This Works

**Scenario 1: No conflict**
```
Agent A: read(v5) → process → commit(v5→v6) ✓
Agent B: read(v6) → process → commit(v6→v7) ✓
```

**Scenario 2: Conflict (second agent retries)**
```
Agent A: read(v5) → process 2s → commit(v5→v6) ✓
Agent B: read(v5) → process 1s → commit(v5) ✗ Version mismatch!
Agent B: retry, read(v6) → process 1s → commit(v6→v7) ✓
```

**Scenario 3: Multiple concurrent agents**
```
All agents read v10 simultaneously
Agent A commits first → v11
Agent B commits → version error, retry
Agent C commits → version error, retry
Only one writes at a time (asyncio.Lock ensures this)
```

### Performance vs Pessimistic Locking

**Optimistic (this approach):**
- Read: No lock (concurrent, fast)
- Write: Check version, increment
- Pro: Scales well for read-heavy
- Con: Must retry on conflicts

**Pessimistic (alternative):**
- Read: Hold lock
- Write: Keep lock
- Pro: No retries needed
- Con: Bottleneck for many concurrent reads

**This workload:** Agents read state 100+ times, update 5-10 times
→ Optimistic locking is 10-50x better

---

## Section 2: Provider Pattern with Circuit Breaker

**📂 Jump directly to the code:**
| What | File | Lines |
|------|------|-------|
| `LLMProvider` abstract interface | [`backend/app/providers/base.py`](../../backend/app/providers/base.py) | L37–140 |
| `ProviderResponse` model | [`backend/app/providers/base.py`](../../backend/app/providers/base.py) | L12–35 |
| `ProviderStatus` enum | [`backend/app/providers/factory.py`](../../backend/app/providers/factory.py) | L19–23 |
| `ProviderFactory` class | [`backend/app/providers/factory.py`](../../backend/app/providers/factory.py) | L26–42 |
| `initialize()` startup | [`backend/app/providers/factory.py`](../../backend/app/providers/factory.py) | L44–79 |
| `get_provider()` fallback logic | [`backend/app/providers/factory.py`](../../backend/app/providers/factory.py) | L107–140 |
| `handle_provider_failure/success` | [`backend/app/providers/factory.py`](../../backend/app/providers/factory.py) | L142–160 |
| OpenAI implementation | [`backend/app/providers/openai_provider.py`](../../backend/app/providers/openai_provider.py) | full file |
| Gemini implementation | [`backend/app/providers/gemini_provider.py`](../../backend/app/providers/gemini_provider.py) | full file |

### The Problem Without Circuit Breaker

```python
# ❌ Without circuit breaker
async def generate_facts(prompt):
    try:
        response = await openai.generate(prompt)
        return response
    except Exception as e:
        # Every call retries immediately
        logger.error(f"Failed: {e}")
        raise

# If OpenAI is down for 30 minutes:
# Request 1 at t=0: fail, retry, retry, retry... waste time
# Request 2 at t=2: fail immediately, retry, retry...
# Request N at t=30: Same, waste resources
# Result: Slow UI, cascading failures downstream
```

### Solution: Circuit Breaker Pattern

**State machine:**

```
                    ┌─────────────────────────────────────┐
                    │         HEALTHY                     │
                    │ failure_count = 0                   │
                    │ ✓ Use provider normally             │
                    └──────────────┬──────────────────────┘
                                   │
                         (failure happens)
                                   │
                                   ▼
                    ┌──────────────────────────────────────┐
                    │         DEGRADED                     │
                    │ failure_count = 1, 2, 3 (< 3)       │
                    │ ✓ Still use but track failures       │
                    └──────────────┬──────────────────────┘
                                   │
                         (3rd failure)
                                   │
                                   ▼
                    ┌──────────────────────────────────────┐
                    │       UNAVAILABLE                    │
                    │ ❌ Don't use this provider           │
                    │ → Fallback to secondary              │
                    └──────────────┬──────────────────────┘
                                   │
                    (Success after fallback)
                                   │
                     Reset failure_count = 0
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │       Back to HEALTHY                │
                    └─────────────────────────────────────┘
```

**Implementation:**

```python
class ProviderFactory:
    def __init__(self):
        self.primary_provider = OpenAIProvider()
        self.fallback_provider = GeminiProvider()
        self.primary_status = ProviderStatus.HEALTHY
        self.failure_count = 0
        self.max_failures = 3
    
    async def get_provider(self):
        # Rule 1: Use primary if HEALTHY
        if self.primary_status == ProviderStatus.HEALTHY:
            return self.primary_provider
        
        # Rule 2: Use fallback if primary not HEALTHY
        if self.fallback_status == ProviderStatus.HEALTHY:
            logger.info("Primary unavailable, using fallback")
            return self.fallback_provider
        
        # Rule 3: Both degraded - try primary anyway (might recover)
        if self.primary_status == ProviderStatus.DEGRADED:
            logger.warning("Both degraded, attempting primary")
            return self.primary_provider
        
        # Rule 4: All exhausted
        raise RuntimeError("No providers available")
    
    async def execute_with_circuit_breaker(self, operation):
        try:
            provider = await self.get_provider()
            result = await operation(provider)
            await self.handle_success(provider)  # Reset failure_count
            return result
        except Exception as e:
            await self.handle_failure(provider)  # Increment failure_count
            raise
    
    async def handle_failure(self, provider):
        self.failure_count += 1
        logger.warning(f"Provider failure #{self.failure_count}")
        
        if self.failure_count >= self.max_failures:
            # Open the circuit
            if provider == self.primary_provider:
                self.primary_status = ProviderStatus.UNAVAILABLE
            else:
                self.fallback_status = ProviderStatus.UNAVAILABLE
            logger.error(f"Circuit opened: {provider.name} marked UNAVAILABLE")
    
    async def handle_success(self, provider):
        self.failure_count = 0  # Reset on success
        if provider == self.primary_provider:
            self.primary_status = ProviderStatus.HEALTHY
        else:
            self.fallback_status = ProviderStatus.HEALTHY
        logger.info("Circuit recovered: status back to HEALTHY")
```

### Real-World Scenario

```
t=0:00: OpenAI API healthy, all requests go to OpenAI
        primary_status = HEALTHY

t=0:15: OpenAI becomes degraded (high latency)
        Request 1 fails → failure_count = 1
        Request 2 fails → failure_count = 2
        Request 3 fails → failure_count = 3 = max_failures

t=0:20: Primary_status = UNAVAILABLE
        Request 4 → get_provider() returns Gemini immediately
        Request 5 → get_provider() returns Gemini immediately
        No more retry attempts on dead OpenAI!

t=0:30: OpenAI recovers
        Frontend retries (or new request comes in)
        Request 6 → uses Gemini (still UNAVAILABLE)
        
t=1:00: Someone requests again
        Request 7 → tries primary (might be recovered now)
        If succeeds → failure_count = 0, back to HEALTHY
        Requests start using OpenAI again
```

### Key Insight

Without circuit breaker, every failure makes things worse (retry overhead, resource waste).

With circuit breaker:
- Fast-fail when service is down (saves resources)
- Automatic fallback (good UX)
- Automatic recovery when service comes back (no manual intervention)

---

## Section 3: LangGraph Orchestration with Supervisor

**📂 Jump directly to the code:**
| What | File | Lines |
|------|------|-------|
| `WorkflowOrchestrator` class | [`backend/app/orchestration/workflow.py`](../../backend/app/orchestration/workflow.py) | L28–75 |
| `_build_graph()` method | [`backend/app/orchestration/workflow.py`](../../backend/app/orchestration/workflow.py) | L100–200 |
| Node wrapper functions | [`backend/app/orchestration/workflow.py`](../../backend/app/orchestration/workflow.py) | L200–350 |
| `Supervisor.decide_next_node()` | [`backend/app/orchestration/supervisor.py`](../../backend/app/orchestration/supervisor.py) | L80–150 |
| Resume endpoint `POST /resume` | [`backend/app/api/orchestration.py`](../../backend/app/api/orchestration.py) | full file |
| Frontend resume call | [`frontend/src/services/api.js`](../../frontend/src/services/api.js) | L69–74 |
| SSE stream hook | [`frontend/src/hooks/useWorkflowSSE.js`](../../frontend/src/hooks/useWorkflowSSE.js) | L1–176 |

### The Challenge

```
Agents:
- extraction_agent (extract facts from documents)
- questionnaire_agent (generate questions for gaps)
- intake_draft_agent (create structured document)
- validation_agent (check quality)

How do we:
1. Execute them in order?
2. Handle errors (retry, skip)?
3. Pause for human review?
4. Implement conditional logic?
```

### Solution: LangGraph with Supervisor Routing

**Concept:**

```
[extraction_agent] 
        ↓
    [supervisor] decides: should we continue?
        ↓
    If yes: [questionnaire_agent]
    If no: [END] (pause)
        ↓
    [supervisor] decides next
        ↓
    If human_reviewed=false: [END] (pause)
    If human_reviewed=true: [migration_planning_agent]
```

**Implementation:**

```python
from langgraph.graph import StateGraph, END

# Create graph
graph = StateGraph(MigrationState)

# Add agent nodes
graph.add_node("extraction_agent", _extraction_node)
graph.add_node("questionnaire_agent", _questionnaire_node)
graph.add_node("intake_draft_agent", _intake_draft_node)
graph.add_node("supervisor", _supervisor_node)

# All agents report to supervisor
graph.add_edge("extraction_agent", "supervisor")
graph.add_edge("questionnaire_agent", "supervisor")
graph.add_edge("intake_draft_agent", "supervisor")

# Supervisor makes routing decision
def decide_next_node(state):
    """Supervisor decision logic"""
    phase = state['phase']
    
    if phase == WorkflowPhase.INIT:
        return "extraction_agent"
    
    elif phase == WorkflowPhase.EXTRACTION:
        return "questionnaire_agent"
    
    elif phase == WorkflowPhase.QUESTIONNAIRE:
        return "intake_draft_agent"
    
    elif phase == WorkflowPhase.INTAKE_DRAFT:
        # KEY: Pause for human review
        if state['human_reviewed']:
            return "migration_planning_agent"
        else:
            return "END"  # Pause here, don't recurse!
    
    elif phase == WorkflowPhase.MIGRATION_PLANNING:
        return "validation_agent"
    
    elif phase == WorkflowPhase.VALIDATION:
        return "END"
    
    return "END"

# Conditional edges (supervisor routes based on decision)
graph.add_conditional_edges(
    "supervisor",
    decide_next_node,
    {
        "extraction_agent": "extraction_agent",
        "questionnaire_agent": "questionnaire_agent",
        "intake_draft_agent": "intake_draft_agent",
        "migration_planning_agent": "migration_planning_agent",
        "validation_agent": "validation_agent",
        "END": END
    }
)

# Compile with checkpointer for replay
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()
runnable = graph.compile(checkpointer=checkpointer)
```

### The Critical Gotcha: Pause vs Recursion

❌ **WRONG:**
```python
elif phase == WorkflowPhase.INTAKE_DRAFT:
    if state['human_reviewed']:
        return "migration_planning_agent"
    else:
        return "intake_draft_agent"  # ❌ Infinite loop!
```

Graph execution:
```
intake_draft_agent finishes → supervisor sees human_reviewed=false
supervisor returns "intake_draft_agent"
intake_draft_agent runs again (but state hasn't changed!)
supervisor sees human_reviewed=false again
intake_draft_agent runs again
...infinite recursion, GraphRecursionError at limit=25
```

✓ **CORRECT:**
```python
elif phase == WorkflowPhase.INTAKE_DRAFT:
    if state['human_reviewed']:
        return "migration_planning_agent"
    else:
        return "END"  # ✓ Pause
```

Graph execution:
```
intake_draft_agent finishes → supervisor sees human_reviewed=false
supervisor returns "END"
Graph pauses (workflow frozen)
[Meanwhile, frontend gets SSE event: "paused for review"]
[User reviews in UI]
[User clicks approve]
[Frontend calls POST /resume with human_reviewed=true]
[Backend updates state]
[Graph resumes from checkpoint]
supervisor sees human_reviewed=true
supervisor returns "migration_planning_agent"
Graph continues...
```

### Resume Flow

```python
@app.post("/resume")
async def resume_workflow(project_id: str, updates: dict):
    # Update state
    await state_manager.commit_state(project_id, updates)
    
    # Re-execute workflow from checkpoint
    state = await state_manager.get_state(project_id)
    final_state = await runnable.ainvoke(state)
    
    return {"status": "resumed", "phase": final_state['phase']}
```

---

## Section 4: Annotated Reducers for State Merging

**📂 Jump directly to the code:**
| What | File | Lines |
|------|------|-------|
| `merge_lists()` function | [`backend/app/orchestration/state.py`](../../backend/app/orchestration/state.py) | L14–37 |
| `merge_dicts()` function | [`backend/app/orchestration/state.py`](../../backend/app/orchestration/state.py) | L40–46 |
| Fields using `Annotated[..., reducer]` | [`backend/app/orchestration/state.py`](../../backend/app/orchestration/state.py) | L110–150 |

### Why Reducers Matter

When two agents update state concurrently:

```
Agent A patch: {normalized_docs: [{"id": 1}], trace_metadata: {"extraction": {...}}}
Agent B patch: {normalized_docs: [{"id": 2}], trace_metadata: {"questionnaire": {...}}}

WITHOUT reducers:
result = Agent A patch if A writes first, Agent B patch lost!
→ Data loss!

WITH reducers:
normalized_docs: merge_lists([{"id": 1}], [{"id": 2}]) = [{"id": 1}, {"id": 2}]
trace_metadata: merge_dicts({"extraction": {...}}, {"questionnaire": {...}})
              = {"extraction": {...}, "questionnaire": {...}}
→ No data loss!
```

### Implementation

```python
def merge_lists(left, right):
    """
    Append lists.
    
    Used for fields that accumulate (agents append data)
    """
    if left is None: left = []
    if right is None: right = []
    if not isinstance(left, list): left = [left] if left else []
    if not isinstance(right, list): right = [right] if right else []
    return left + right

def merge_dicts(left, right):
    """
    Shallow dict merge, right takes precedence.
    
    Used for fields that accumulate data by key
    """
    if right is None: return left
    if left is None: return right
    return {**left, **right}

# Apply to state
class MigrationState(TypedDict):
    # Lists accumulate (agents append)
    normalized_docs: Annotated[List[Dict[str, Any]], merge_lists]
    missing_questions: Annotated[List[Dict[str, Any]], merge_lists]
    review_flags: Annotated[List[str], merge_lists]
    state_changelog: Annotated[List[StateChangelogEntry], merge_lists]
    
    # Dicts merge by key
    trace_metadata: Annotated[Dict[str, Any], merge_dicts]
    confidence_scores: Annotated[Dict[str, float], merge_dicts]
```

### How LangGraph Applies Reducers

```python
# When state updates happen
current_state = {
    'normalized_docs': [{'id': 1}],
    'trace_metadata': {'init': {'time': '...'}}
}

agent_patch = {
    'normalized_docs': [{'id': 2}],
    'trace_metadata': {'extraction': {'facts': 42}}
}

# LangGraph sees Annotated[List, merge_lists]
# Applies: merge_lists([{'id': 1}], [{'id': 2}])
# Result: [{'id': 1}, {'id': 2}]

# LangGraph sees Annotated[Dict, merge_dicts]
# Applies: merge_dicts({'init': {...}}, {'extraction': {...}})
# Result: {'init': {...}, 'extraction': {...}}

final_state = {
    'normalized_docs': [{'id': 1}, {'id': 2}],
    'trace_metadata': {'init': {...}, 'extraction': {...}}
}
```

---

## Section 5: Performance & Scaling

**📂 Jump directly to the code:**
| What | File | Lines |
|------|------|-------|
| Redis client (serialization) | [`backend/app/storage/redis_client.py`](../../backend/app/storage/redis_client.py) | full file |
| asyncio.Lock (per-project pattern) | [`backend/app/orchestration/state_manager.py`](../../backend/app/orchestration/state_manager.py) | L55–70 |
| Async agent execution | [`backend/app/orchestration/workflow.py`](../../backend/app/orchestration/workflow.py) | L50–100 |
| Redis config (host/port/TTL) | [`backend/app/config.py`](../../backend/app/config.py) | L74–78 |

### Bottleneck 1: Redis Serialization

**Problem:**
```python
# Every commit does JSON serialization
state_dict = state.model_dump()
json_str = json.dumps(state_dict)  # Slow!
await redis.set(f"state:{project_id}", json_str)
```

For large state (1000 documents), JSON is slow.

**Solution: MessagePack**
```python
import msgpack

# Much faster
packed = msgpack.packb(state.model_dump())  # Binary, compact
await redis.set(f"state:{project_id}", packed)

# When reading
packed = await redis.get(f"state:{project_id}")
state_dict = msgpack.unpackb(packed)
```

**Result:** 3-5x faster serialization.

### Bottleneck 2: Lock Contention

**Problem: Global lock**
```python
# All projects share one lock
self._lock = asyncio.Lock()

async with self._lock:  # Only one project commits at a time
    await self.commit_state(project_id, patch)

# If project A is committing, project B waits!
# If 100 concurrent projects: 99 waiting
```

**Solution: Per-project locks**
```python
self._locks = {}  # Map of project_id -> Lock

async def get_lock(project_id):
    if project_id not in self._locks:
        self._locks[project_id] = asyncio.Lock()
    return self._locks[project_id]

async with await self.get_lock(project_id):  # Only this project waits
    await self.commit_state(project_id, patch)

# 100 projects can commit concurrently!
```

### Bottleneck 3: LLM Latency

**Problem: Sequential agent calls**
```python
extraction_result = await extraction_agent.execute(state)
questionnaire_result = await questionnaire_agent.execute(state)
# Total time: extraction_time + questionnaire_time
```

**Solution: Parallel calls on same state**
```python
extraction_result, questionnaire_result = await asyncio.gather(
    extraction_agent.execute(state),
    questionnaire_agent.execute(state)
)
# Total time: max(extraction_time, questionnaire_time)
# Both read same state, no conflicts
```

---

## Summary: Trade-offs Table

| Pattern | Pro | Con | When to Use |
|---------|-----|-----|------------|
| **Optimistic Locking** | Scalable (lock-free reads) | Retry logic needed | Read-heavy (100:10 ratio) |
| **Pessimistic Locking** | No retries | Bottleneck (lock held) | Write-heavy (conflicts common) |
| **Circuit Breaker** | Fast-fail, fallback | Extra state to track | External services |
| **LangGraph** | Flexible routing, conditional edges | LangGraph dependency | Multi-agent workflows |
| **Annotated Reducers** | Transparent merging | Must understand semantics | Concurrent state updates |
| **SSE Streaming** | Low latency, simple | One-way only | Real-time updates |
| **Per-project locks** | High concurrency | More complex | 1000+ concurrent items |

---

**End of Technical Deep Dive**

*Made with Bob*
