# 4-Hour Deep Dive Path

**Comprehensive System Design Interview Preparation**

For serious preparation or deep understanding.

---

## 📅 Schedule (4 hours total)

- **Hour 1 (60 min):** Technical foundation - State Management
- **Hour 2 (60 min):** Resilience patterns - Providers & Error Recovery  
- **Hour 3 (60 min):** System design questions (live practice)
- **Hour 4 (60 min):** Whiteboarding 3 designs + review

---

## Hour 1: Technical Foundation — State Management (60 min)

### Part A: Immutable State Concept (15 min)

**File:** `00-START-HERE.md` + `QUICK-REFERENCE.md` Pattern 1

**Study:**
- Why immutable state is better than mutable
- Versioning mechanism (state_version field)
- Optimistic locking: version checking at commit time

**Practice:**
Imagine: Agent A reads version 5, Agent B reads version 5
- Agent A processes for 2 seconds
- Agent B processes for 1 second, writes first → version becomes 6
- Agent A tries to write from version 5 → version mismatch! What happens?

**Answer:** Agent A retries, reads version 6, processes again, writes as version 7.

### Part B: Annotated Reducers (15 min)

**File:** `QUICK-REFERENCE.md` Pattern 4

**Study:**
```python
# When two agents update state concurrently:

# Lists: merge_lists(left, right) = left + right
normalized_docs: Annotated[List[Dict], merge_lists]

# Dicts: merge_dicts(left, right) = {**left, **right}
trace_metadata: Annotated[Dict[str, Any], merge_dicts]
```

**Practice:**
- Agent A adds 2 documents
- Agent B adds 3 documents
- What's the result? (Answer: 5 documents, all appended)

- Agent A sets extraction: {facts: 42}
- Agent B sets questionnaire: {questions: 100}
- What's the result? (Answer: Both keys present, merged)

### Part C: Optimistic Locking in Practice (15 min)

**File:** `SYSTEM-DESIGN-QUESTIONS.md` Q1 → "Optimistic Locking Implementation" section

**Study the code:**
```python
async def commit_state(self, project_id, patch):
    async with self._lock:
        current = await self.get_state(project_id)
        read_version = current['state_version']
        
        # KEY LINE
        if current['state_version'] != read_version:
            raise StateTransactionError("Version mismatch")
        
        # Proceed with update
        new_state = {..., 'state_version': read_version + 1}
```

**Deep dive:**
- Why only hold lock at commit (not during processing)?
- How does this scale to 1000 concurrent agents?
- What's the downside? (Retry loops on high conflict)

### Part D: Changelog & Audit Trail (15 min)

**File:** `SYSTEM-DESIGN-QUESTIONS.md` Q1 → "Audit Trail" section

**Study:**
- Every commit creates changelog entry
- Entry includes: version, patch, committed_by, timestamp, reason
- Enables: replay, rollback, compliance

**Practice:**
Design a recovery scenario: "Workflow crashed at version 12. How do you recover?"

Answer: Restore from checkpoint (v10), replay changelog entries (v10→v11→v12).

---

## Hour 2: Resilience Patterns (60 min)

### Part A: Circuit Breaker States & Transitions (15 min)

**File:** `QUICK-REFERENCE.md` Pattern 2 + `SYSTEM-DESIGN-QUESTIONS.md` Q3

**Study the three states:**

```
State 1: HEALTHY
├─ Use provider normally
├─ Track failure_count = 0
└─ On failure → increment count, go to DEGRADED

State 2: DEGRADED  
├─ Still use provider (with caution)
├─ failure_count = 1, 2, 3...
└─ On 3rd failure → go to UNAVAILABLE

State 3: UNAVAILABLE
├─ Don't use this provider
├─ Fallback to secondary immediately
├─ On success (after fallback) → reset count, back to HEALTHY
└─ Prevents hammering dead service
```

**Practice question:** "What if OpenAI times out 3 times, then recovers 30 seconds later?"
**Answer:**
1. After 3 failures, marked UNAVAILABLE
2. Requests switch to Gemini
3. After 30 seconds, someone tries OpenAI again
4. If succeeds → reset failure_count to 0, back to HEALTHY
5. Requests start using OpenAI again

### Part B: Error Recovery Layers (15 min)

**File:** `QUICK-REFERENCE.md` Pattern 5 + `SYSTEM-DESIGN-QUESTIONS.md` Q5

**Study the 4 layers:**

```
Layer 1: Agent Level
└─ Try/catch around LLM call
└─ Return error patch dict (no exceptions)
└─ Example: "LLM timeout, return facts=None"

Layer 2: Node Level  
└─ Catch exceptions from agent
└─ Log with full traceback (exc_info=True)
└─ Return error state patch
└─ Example: "Agent threw exception, log it, mark ERROR"

Layer 3: Supervisor Level
└─ Check retry_count < max_retries
└─ Route back to same node (retry)
└─ Or route to ERROR phase if exhausted
└─ Example: "Retry_count=2, try extraction again"

Layer 4: API Level
└─ Catch StateTransactionError (version mismatch)
└─ Return 409 Conflict (client should retry)
└─ Catch other exceptions
└─ Return 500 Internal Server Error
└─ Example: "Version mismatch, client retries"
```

**Practice:** "LLM times out on attempt 1, 2, 3. What happens at each layer?"
- Layer 1: Agent returns error patch
- Layer 2: Node catches (if any exception), logs, returns error patch
- Layer 3: Supervisor sees retry_count < 3, reruns extraction_agent
- If attempt 4 also fails: Supervisor sees retry_count = 3 = max_retries, routes to ERROR phase
- Layer 4: API eventually returns error to user

### Part C: Retry with Exponential Backoff (15 min)

**File:** `QUICK-REFERENCE.md` Pattern 6

**Study:**
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def fetch_from_mcp(profile):
    pass

# Attempt 1: Immediate, fail
# Sleep: 2-4 seconds (random between min=2, max=10^1=10)
# Attempt 2: Retry, fail
# Sleep: 4-8 seconds (random between min=2, max=10^2=100 but capped at 10)
# Attempt 3: Retry, fail
# Raise exception
```

**Key insight:** Why exponential?
- Transient failures (network glitch) often resolve quickly
- Exponential backoff gives downstream service time to recover
- If you keep hammering immediately, you prevent recovery

### Part D: Dependency Injection Pattern (15 min)

**File:** `QUICK-REFERENCE.md` Pattern 7

**Study:**
```python
# Define how to get a dependency
async def get_state_manager() -> StateManager:
    if not hasattr(get_state_manager, 'instance'):
        get_state_manager.instance = StateManager()
    return get_state_manager.instance

# Inject into endpoint
@app.post("/execute")
async def execute_workflow(
    manager: Annotated[StateManager, Depends(get_state_manager)]
):
    # manager is injected
    pass
```

**Benefits:**
- Easy to mock for testing
- Can swap implementations (test vs production)
- Follows SOLID principles (Dependency Inversion)

---

## Hour 3: System Design Questions (Live Practice) (60 min)

**File:** `SYSTEM-DESIGN-QUESTIONS.md`

You're going to do 3 questions. Pick your pace:

### Option A: Full Deep Dive (Choose 1)
- Q1: Workflow state management (20 min read, 20 min reflect, 20 min practice answer)

### Option B: Medium Dive (Choose 2)
- Q3: Fault-tolerant LLM providers (15 min)
- Q4: Multi-phase workflow with human review (15 min)

### Option C: Quick Coverage (Choose 3)
- Q3: Fault-tolerant LLM (12 min)
- Q4: Multi-phase workflow (12 min)
- Q6: Optimize for high throughput (12 min)
- Q7: Data consistency (12 min)

**For each question:**
1. Read the problem
2. Close the file
3. Whiteboard your answer (5-10 min)
4. Compare with provided answer
5. Note differences

---

## Hour 4: Whiteboarding Practice & Review (60 min)

### Part A: Whiteboard Design 1 - Q1 (20 min)

**Question:** "Design workflow state management for AI agents"

**Your turn:** Use the template from `QUICK-REFERENCE.md`

```
1. PROBLEM (what are we solving?)
2. CONSTRAINTS (what are the requirements?)
3. HIGH LEVEL (architecture diagram)
4. DEEP DIVE: State management (explain optimistic locking)
5. DEEP DIVE: Resilience (error recovery)
6. SCALE: 1000 workflows (sharding, per-project locks)
7. MONITORING: Track what?
```

**When done:** Compare with `SYSTEM-DESIGN-QUESTIONS.md` → Q1

### Part B: Whiteboard Design 2 - Q3 (20 min)

**Question:** "Design fault-tolerant LLM provider system"

**Your turn:** Whiteboard the circuit breaker pattern

```
1. PROBLEM (OpenAI can fail)
2. CONSTRAINTS (need fallback)
3. HIGH LEVEL (two providers)
4. DEEP DIVE: Circuit breaker states (draw 3 boxes)
5. DEEP DIVE: Fallback logic (when to switch)
6. SCALE: Rate limiting, health checks
7. MONITORING: Track which provider is active
```

**When done:** Compare with `SYSTEM-DESIGN-QUESTIONS.md` → Q3

### Part C: Whiteboard Design 3 - Q6 (15 min)

**Question:** "Optimize for high throughput (100 concurrent workflows)"

**Your turn:** Think about:
- Serialization overhead (JSON → MessagePack)
- Lock contention (per-project locks)
- Parallelization (concurrent agent calls)

**When done:** Compare with `SYSTEM-DESIGN-QUESTIONS.md` → Q6

### Part D: Review & Reflection (5 min)

**For each design:**
- What did you get right?
- What did you miss?
- What would you do differently next time?

---

## Key Concepts You Now Understand

After Hour 1-4, you should be able to:

- [ ] Explain optimistic locking (version checking at commit)
- [ ] Draw circuit breaker state diagram (3 states, 3 transitions)
- [ ] Describe 4-layer error recovery
- [ ] Discuss Annotated reducers (list append, dict merge)
- [ ] Design a fault-tolerant provider system
- [ ] Handle state management with concurrent agents
- [ ] Whiteboard a complete system design
- [ ] Discuss trade-offs (why X over Y)

---

## Interview Day

You're ready! Remember:

1. **Listen carefully** — Understand constraints
2. **Ask questions** — "How many users? What's latency SLA?"
3. **Draw diagrams** — Simple boxes and arrows
4. **Think out loud** — "So if this happens, then..."
5. **Discuss trade-offs** — Show you understand pros/cons
6. **Reference patterns** — "We'd use circuit breaker here"
7. **Stay calm** — You've studied real production code

---

**You've completed deep preparation!** 🎓

*Made with Bob*
