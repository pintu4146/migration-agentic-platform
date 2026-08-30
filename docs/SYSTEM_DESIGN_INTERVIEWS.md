# System Design Interview Questions & Answers

**For 5+ Years of Experience Backend Engineers**

Based on actual patterns from IBM Migration Copilot

---

## Part 1: State Management Design

### Q1: Design a workflow state management system for multi-agent AI

**Context:** You have 5 AI agents (extraction, questionnaire, validation, etc.) that read/update shared workflow state. Agents can run sequentially or with some parallelism. State changes must be auditable, recoverable, and support concurrent updates.

**Answer Outline:**

**1. State Schema (TypedDict with Version Control)**
```
Requirements:
- Immutable state (agents propose patches, not direct modifications)
- Version tracking (detect lost updates)
- Audit trail (compliance/debugging)
- Concurrent safety (multiple agents reading simultaneously)
```

**Design:**
```python
class MigrationState(TypedDict):
    # Identity
    project_id: str
    state_version: int  # Optimistic locking
    phase: WorkflowPhase
    
    # Lists with merge_lists reducer
    normalized_docs: Annotated[List[Dict], merge_lists]
    missing_questions: Annotated[List[Dict], merge_lists]
    
    # Dicts with merge_dicts reducer
    trace_metadata: Annotated[Dict[str, Any], merge_dicts]
    
    # Audit
    state_changelog: Annotated[List[StateChangelogEntry], merge_lists]
```

**2. Transaction Model (Optimistic Locking)**
```
Agent A: read(v5) ──> [process] ──> write(v5→v6) ✓
Agent B: read(v5) ──> [process] ──> write(v5→v6) ✗ (version mismatch)
Agent B: retry, read(v6) ──> [process] ──> write(v6→v7) ✓
```

**Pros:**
- Lock-free reads (scale to many agents)
- Detects conflicts at commit time
- Supports retry logic

**Cons:**
- Must handle retry loops (track attempt count)
- Increased latency if conflicts frequent

**3. Concurrency Control**
```
asyncio.Lock around commit() ensures:
- Only one agent writes at a time
- Version check + write is atomic
- Changelog updated atomically
```

**4. Audit Trail**
```python
state_changelog: [
    {version: 1, patch: {...}, committed_by: 'init', reason: '...'},
    {version: 2, patch: {...}, committed_by: 'agent-extraction', reason: '...'},
    {version: 3, patch: {...}, committed_by: 'agent-questionnaire', reason: '...'},
]
```

**5. Recovery Strategy**
```
Checkpoint every N commits:
- v1-5: saved in Redis
- v5-10: checkpoint, saved in backup storage
- v10-15: another checkpoint

If crash at v12:
- Restore from checkpoint (v10)
- Replay changelog v10→v12
```

**Trade-offs:**
| Aspect | Chosen | Alternative |
|--------|--------|-------------|
| Locking | Optimistic | Pessimistic (slower) |
| Merging | Custom reducers | Last-write-wins (loses data) |
| Audit | Full changelog | No audit (risk) |
| Storage | Redis + backup | Database (slower) |

---

### Q2: How would you scale this to 1000 concurrent workflows?

**Answer:**

**1. Redis Sharding**
```
state:{project_id_hash % N}
where N = number of Redis nodes

Project 1: Redis node 1
Project 2: Redis node 3
Project 3: Redis node 2
...
```

**2. Distributed Lock (Redis SETEX)**
```python
# Instead of asyncio.Lock (single process only)
async def acquire_lock(project_id):
    key = f"lock:{project_id}"
    # SET if not exists, with expiry
    return await redis.set(key, "1", nx=True, ex=10)

# Prevents lock from hanging if process dies
```

**3. Batch Commits**
```python
# Instead of writing on every update
# Collect patches and commit every N seconds
pending_patches = {}

async def queue_patch(project_id, patch):
    if project_id not in pending_patches:
        pending_patches[project_id] = {}
    # Merge patches
    pending_patches[project_id].update(patch)

async def flush_patches():
    for project_id, patch in pending_patches.items():
        await state_manager.commit_state(project_id, patch)
```

**4. Monitoring & Alerting**
```
Metrics:
- Commit latency (p50, p95, p99)
- Conflict rate (retry failures)
- Lock contention (time spent waiting)
- State size (GBs of state)
```

---

## Part 2: Provider Pattern & Resilience

### Q3: Design a fault-tolerant LLM provider system with fallback

**Context:** Your system uses multiple LLM providers (OpenAI, Gemini, Anthropic). Any can fail, be slow, or rate-limited. You need graceful degradation.

**Answer:**

**1. Abstract Interface (Strategy Pattern)**
```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt): pass
    
    @abstractmethod
    async def generate_structured(self, prompt, schema): pass
    
    @abstractmethod
    async def health_check(self): pass
```

**2. Circuit Breaker Pattern**
```
HEALTHY ─(failure)─> DEGRADED ─(max_failures)─> UNAVAILABLE
   ▲                                                    │
   └────────(success resets counter)──────────────────┘

States:
- HEALTHY: Use, track failures
- DEGRADED: Use but prepare to switch
- UNAVAILABLE: Fast-fail, don't retry
```

**3. Implementation**
```python
class ProviderFactory:
    def __init__(self):
        self.primary_provider = OpenAIProvider()
        self.fallback_provider = GeminiProvider()
        self.primary_status = ProviderStatus.HEALTHY
        self.failure_count = 0
    
    async def get_provider(self):
        # Try primary if healthy
        if self.primary_status == ProviderStatus.HEALTHY:
            return self.primary_provider
        
        # Try fallback
        if self.fallback_status == ProviderStatus.HEALTHY:
            return self.fallback_provider
        
        # All down: attempt degraded state
        raise RuntimeError("No providers available")
    
    async def handle_failure(self, provider):
        self.failure_count += 1
        if self.failure_count >= 3:
            provider.status = ProviderStatus.UNAVAILABLE
        else:
            provider.status = ProviderStatus.DEGRADED
    
    async def handle_success(self, provider):
        self.failure_count = 0
        provider.status = ProviderStatus.HEALTHY
```

**4. Failure Modes**
```
Scenario 1: OpenAI timeout
→ failure_count++
→ Still use OpenAI (retry logic)
→ Next success: reset counter

Scenario 2: OpenAI consistently times out (3x)
→ Mark UNAVAILABLE
→ get_provider() returns Gemini
→ Requests now use Gemini

Scenario 3: Gemini also fails
→ Raise RuntimeError("No providers")
→ API returns 503 Service Unavailable
→ Frontend shows "temporarily unavailable"

Scenario 4: OpenAI recovers
→ Client retries with exponential backoff
→ Eventually OpenAI succeeds
→ Reset failure_count to 0, back to HEALTHY
```

**5. Monitoring**
```python
@app.get("/health/providers")
async def provider_health():
    return {
        "primary": {
            "provider": "openai",
            "status": factory.primary_status,
            "failure_count": factory.failure_count,
            "model": "gpt-4-turbo"
        },
        "fallback": {
            "provider": "gemini",
            "status": factory.fallback_status,
            "model": "gemini-1.5-pro"
        },
        "active_provider": "gemini" if factory.primary_status != HEALTHY else "openai"
    }
```

---

## Part 3: Workflow Orchestration

### Q4: Design a multi-phase workflow with pauses for human review

**Context:** Workflow phases: init → extraction → questionnaire → intake_draft → **human_review** → migration_planning → validation → complete. After intake_draft, workflow pauses for human review. Only resumes when human approves.

**Answer:**

**1. LangGraph State Graph**
```python
graph = StateGraph(MigrationState)

# Add nodes
graph.add_node("extraction_agent", _extraction_node)
graph.add_node("questionnaire_agent", _questionnaire_node)
graph.add_node("intake_draft_agent", _intake_draft_node)
graph.add_node("supervisor", _supervisor_node)

# Edges: agents → supervisor (supervisor routes next)
graph.add_edge("extraction_agent", "supervisor")
graph.add_edge("questionnaire_agent", "supervisor")
graph.add_edge("intake_draft_agent", "supervisor")

# Conditional edges: supervisor → next node or END
graph.add_conditional_edges(
    "supervisor",
    decide_next_node,
    {
        "extraction_agent": "extraction_agent",
        "questionnaire_agent": "questionnaire_agent",
        "intake_draft_agent": "intake_draft_agent",
        "END": END
    }
)

# Checkpointer for execution replay
checkpointer = MemorySaver()
runnable = graph.compile(checkpointer=checkpointer)
```

**2. Supervisor Routing Logic**
```python
async def decide_next_node(state: MigrationState) -> str:
    """Supervisor decides next node based on state"""
    
    if state['phase'] == WorkflowPhase.INIT:
        return "extraction_agent"
    
    elif state['phase'] == WorkflowPhase.EXTRACTION:
        return "questionnaire_agent"
    
    elif state['phase'] == WorkflowPhase.QUESTIONNAIRE:
        return "intake_draft_agent"
    
    elif state['phase'] == WorkflowPhase.INTAKE_DRAFT:
        # Special: human review pauses workflow
        if not state['human_reviewed']:
            # Return END to pause (NOT "human_review" node!)
            # ❌ DON'T: would cause infinite loop
            return "END"
        else:
            # Human approved: continue
            return "migration_planning_agent"
    
    elif state['phase'] == WorkflowPhase.MIGRATION_PLANNING:
        return "validation_agent"
    
    elif state['phase'] == WorkflowPhase.VALIDATION:
        return "END"
    
    return "END"
```

**❌ CRITICAL GOTCHA:**
```python
# ❌ WRONG: Routes back to human_review node
if state['phase'] == WorkflowPhase.INTAKE_DRAFT:
    return "human_review"  # ← Graph recurses infinitely!

# ✓ CORRECT: Returns END to pause
if state['phase'] == WorkflowPhase.INTAKE_DRAFT:
    if not state['human_reviewed']:
        return "END"  # Pauses here
    else:
        return "migration_planning_agent"  # Resumes here
```

**3. Frontend Resume Flow**
```
Workflow reaches intake_draft phase:
1. Supervisor checks human_reviewed=false
2. Returns "END" → graph pauses
3. SSE sends phase_transition event
4. Frontend shows "Awaiting review"
5. Human reviews and approves via UI
6. Frontend calls POST /api/orchestration/resume
   {project_id: "proj-1", updates: {human_reviewed: true}}
7. Backend updates state
8. Frontend re-executes workflow
9. Supervisor sees human_reviewed=true
10. Returns "migration_planning_agent"
11. Workflow continues
```

**4. API Implementation**
```python
@app.post("/resume")
async def resume_workflow(request: ResumeWorkflowRequest):
    """Resume workflow from pause (human_review)"""
    
    state = await state_manager.get_state(request.project_id)
    
    # Apply human review approval
    updated_state = {
        'human_reviewed': True,
        'review_timestamp': datetime.utcnow().isoformat(),
        'reviewer_id': current_user_id
    }
    
    # Commit update
    await state_manager.commit_state(
        request.project_id,
        updated_state,
        committed_by='human-reviewer',
        reason='Approved in human review phase'
    )
    
    # Re-execute workflow from checkpoint
    orchestrator = get_workflow_orchestrator()
    await orchestrator.execute_workflow(request.project_id)
    
    return {"status": "resumed", "phase": "migration_planning"}
```

---

## Part 4: Error Recovery & Resilience

### Q5: Design error recovery for a multi-agent workflow

**Context:** During execution, any agent can fail (LLM timeout, validation failure, data error). You need graceful recovery without losing state.

**Answer:**

**1. Error Handling Layers**
```
Layer 1: Agent Level
├─ Try block around LLM call
├─ Catch specific exceptions (timeout, validation)
└─ Return error patch (don't throw)

Layer 2: Node Level
├─ Catch exceptions from agents
├─ Log with full traceback
└─ Route to error state

Layer 3: Supervisor Level
├─ Check retry_count < max_retries
├─ Route to same node again
└─ Or route to ERROR phase if max retries exceeded

Layer 4: API Level
├─ Catch StateTransactionError (version mismatch)
├─ Return 409 Conflict
└─ Client retries
```

**2. Implementation**
```python
async def execute_workflow(self, project_id: str):
    """Execute workflow with error recovery"""
    
    for attempt in range(max_attempts := 3):
        try:
            state = await state_manager.get_state(project_id)
            
            # Run LangGraph
            final_state = await runnable.ainvoke(state)
            
            # Commit final state
            await state_manager.commit_state(project_id, final_state)
            return final_state
        
        except StateTransactionError as e:
            # Version conflict: retry
            logger.warning(f"Version conflict: {e}")
            if attempt < 2:
                await asyncio.sleep(0.5 * (attempt + 1))  # Backoff
                continue
            raise
        
        except Exception as e:
            # Other errors: log and return error state
            logger.error(f"Workflow failed: {e}", exc_info=True)
            
            error_patch = {
                'phase': WorkflowPhase.ERROR,
                'last_error': str(e),
                'retry_count': state['retry_count'] + 1
            }
            
            if state['retry_count'] >= state['max_retries']:
                error_patch['last_error'] = f"Max retries exceeded: {e}"
            
            await state_manager.commit_state(project_id, error_patch)
            raise
```

**3. Checkpoint & Replay**
```python
# Save checkpoint before risky operation
checkpoint_id = await state_manager.create_checkpoint(project_id, state)

try:
    # Execute risky operation
    new_state = await expensive_operation(state)
except Exception as e:
    # Restore from checkpoint
    logger.info(f"Restoring from checkpoint {checkpoint_id}")
    await state_manager.restore_checkpoint(project_id, checkpoint_id)
    raise
```

**4. Monitoring & Alerting**
```
Track:
- Error rate per agent (extraction errors vs questionnaire errors)
- Retry frequency (high retry = problem)
- Phase success rate (which phases fail most?)
- Workflow completion time (SLA breach?)

Alert conditions:
- Error rate > 5% → page on-call
- Retry count > 3 for same phase → auto-escalate
- Workflow stuck in phase > 30 min → notify
```

---

## Part 5: Performance & Scalability

### Q6: How would you optimize for high throughput (100 concurrent workflows)?

**Answer:**

**1. Bottleneck Analysis**
```
Current bottlenecks:
1. Redis serialization (JSON encode/decode each commit)
2. LLM API latency (each agent waits for LLM call)
3. State lock contention (only one write at a time)
```

**2. Optimization Strategies**

**Reduce serialization overhead:**
```python
# Before: JSON on every commit
await redis.set(f"state:{project_id}", json.dumps(state))

# After: Use MessagePack (faster binary serialization)
import msgpack
await redis.set(f"state:{project_id}", msgpack.packb(state))

# Result: 3x faster serialization
```

**Parallelize LLM calls:**
```python
# Before: Sequential
facts = await extraction_agent.execute(state)
questions = await questionnaire_agent.execute(state)

# After: Parallel (same source data)
facts, questions = await asyncio.gather(
    extraction_agent.execute(state),
    questionnaire_agent.execute(state)
)
```

**Reduce lock contention:**
```python
# Before: Lock on every commit
async with self._lock:  # All projects wait here
    await commit(project_id, patch)

# After: Per-project locks
if project_id not in self._locks:
    self._locks[project_id] = asyncio.Lock()

async with self._locks[project_id]:  # Only this project waits
    await commit(project_id, patch)
```

**3. Caching Strategy**
```python
# Cache extracted facts (immutable)
# Cache doesn't change if facts are unchanged
@cache(ttl=3600)
async def get_extracted_facts(project_id):
    return await redis.get(f"facts:{project_id}")

# Cache ML model embeddings
# Expensive to compute, static per document
embeddings_cache = {}
def get_embeddings(doc_id):
    if doc_id in embeddings_cache:
        return embeddings_cache[doc_id]
    embeddings = compute_expensive_embeddings(doc_id)
    embeddings_cache[doc_id] = embeddings
    return embeddings
```

**4. Load Testing**
```python
# Simulate 100 concurrent workflows
import asyncio
import time

async def run_workflow(workflow_id):
    await api_client.post("/start", {"project_id": workflow_id})
    for i in range(50):  # Poll for completion
        state = await api_client.get(f"/state/{workflow_id}")
        if state['phase'] == 'complete':
            return time.time() - start
        await asyncio.sleep(1)

start = time.time()
latencies = await asyncio.gather(
    *[run_workflow(f"proj-{i}") for i in range(100)]
)

p50 = sorted(latencies)[50]
p95 = sorted(latencies)[95]
p99 = sorted(latencies)[99]
print(f"p50={p50}s, p95={p95}s, p99={p99}s")
```

---

## Part 6: Data Consistency & Transactions

### Q7: Ensure consistency when state update fails halfway through

**Context:** Committing state involves: validate patch, check version, update state, log to changelog, write to Redis. If step 4 fails, state is partially updated.

**Answer:**

**1. Transaction Boundaries**
```python
async def commit_state(self, project_id: str, patch: Dict) -> MigrationState:
    """Atomic commit: all-or-nothing"""
    
    async with self._lock:
        # ===== Read Phase =====
        current = await self.redis.get(f"state:{project_id}")
        read_version = current['state_version']
        
        # ===== Validation Phase (no side effects) =====
        self._validate_patch(patch)  # Throws on error
        
        if current['state_version'] != read_version:
            raise StateTransactionError("Version mismatch")
        
        # ===== Computation Phase (no I/O) =====
        new_version = read_version + 1
        changelog_entry = self._create_changelog_entry(...)
        updated_state = {**current, **patch, 'state_version': new_version}
        
        # ===== Write Phase (atomic) =====
        # Either all writes succeed or all fail
        try:
            await self.redis.multi()  # Start transaction
            await self.redis.set(f"state:{project_id}", updated_state)
            await self.redis.lpush(f"changelog:{project_id}", changelog_entry)
            await self.redis.exec()  # Atomic commit
        except RedisError as e:
            await self.redis.discard()
            raise StateTransactionError(f"Redis transaction failed: {e}")
        
        return updated_state
```

**2. Write-Ahead Logging (WAL)**
```python
# Before modifying state, write intent to log
# This way if crash happens, we can recover/retry

async def commit_state_with_wal(self, project_id, patch):
    """Commit with write-ahead log"""
    
    # Step 1: Write intent to log
    intent_id = await self._log_write_intent({
        'project_id': project_id,
        'patch': patch,
        'timestamp': now()
    })
    
    try:
        # Step 2: Perform actual write
        await self._perform_commit(project_id, patch)
        
        # Step 3: Mark intent as committed
        await self._mark_intent_committed(intent_id)
    
    except Exception as e:
        # Intent remains in log
        logger.error(f"Commit failed: {e}, intent_id={intent_id}")
        # Recovery process can replay from log
        raise
```

**3. Idempotency**
```python
# All operations are idempotent: calling twice = calling once

async def commit_state(self, project_id, patch, idempotency_key):
    """Commit with idempotency"""
    
    # Check if we've seen this idempotency key before
    previous_result = await self.redis.get(f"idempotent:{idempotency_key}")
    if previous_result:
        # Already committed: return cached result
        return json.loads(previous_result)
    
    # Perform commit
    updated_state = {...}
    
    # Cache result with idempotency key
    await self.redis.set(
        f"idempotent:{idempotency_key}",
        json.dumps(updated_state),
        ex=3600
    )
    
    return updated_state
```

---

## Summary Table: Key Patterns

| Pattern | Problem | Solution | Trade-off |
|---------|---------|----------|-----------|
| **Optimistic Locking** | Concurrent updates | Version checking at commit | Must handle retries |
| **Circuit Breaker** | Provider failures | Fast-fail, fallback | Needs health checks |
| **SSE Streaming** | Real-time updates | Push from server | Not request/response model |
| **Checkpoint & Replay** | Crash recovery | Save snapshots | Storage overhead |
| **Write-Ahead Logging** | Partial failures | Intent log before write | Added latency |
| **Idempotency** | Retry safety | Idempotency keys | Cache management |
| **Exponential Backoff** | Transient errors | Retry with increasing delays | Slower on repeated failure |

---

## Resources

- LangGraph Documentation: https://langchain-ai.github.io/langgraph/
- Pydantic: https://docs.pydantic.dev/
- FastAPI: https://fastapi.tiangolo.com/
- Redis Transactions: https://redis.io/docs/interact/transactions/
- System Design Primer: https://github.com/donnemartin/system-design-primer

---

**Made with Bob**
