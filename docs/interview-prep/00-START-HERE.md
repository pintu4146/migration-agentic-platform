# Start Here — Interview Preparation Guide

**5 YOE Backend Engineering - Quick Start**

Welcome! This guide will help you prepare for backend interviews using real patterns from IBM Migration Copilot.

---

## ⏱️ How Much Time Do You Have?

### I have 30 minutes
1. Read this file (15 min)
2. Skim `QUICK-REFERENCE.md` (15 min)
3. Focus on: Optimistic Locking, Circuit Breaker, LangGraph

### I have 2 hours
Follow `LEARNING-PATH-2HR.md`

### I have 4+ hours
Follow `LEARNING-PATH-4HR.md`

---

## 🎯 The 5 Core Patterns You Need to Know

### 1. Immutable, Versioned State
**Problem:** Multiple agents update state simultaneously → data loss

**Solution:** Version checking at commit time (optimistic locking)

**Code concept:**
```python
# Current state has version 5
if current['state_version'] != read_version:  # Did someone else update?
    raise StateTransactionError("Version mismatch")  # Yes! Retry with new version
# Write with new version 6
```

**See the actual code:**
- State schema: [`backend/app/orchestration/state.py` (Lines 82-150)](../../backend/app/orchestration/state.py)
  - `MigrationState` TypedDict with `state_version` field
  - `merge_lists()` and `merge_dicts()` reducers
- State manager: [`backend/app/orchestration/state_manager.py` (Lines 37-150)](../../backend/app/orchestration/state_manager.py)
  - `StateManager` class with optimistic locking
  - `commit_state()` method with version checking

**Interview talking point:** "Optimistic locking avoids holding locks during long processing. Better for read-heavy workloads."

**Practice question:** "What happens if two agents read version 5, then both try to write?"
**Answer:** "First one succeeds (v6), second one fails with version mismatch, retries."

---

### 2. Circuit Breaker for Resilience
**Problem:** OpenAI API is down → every request fails → cascade effect

**Solution:** Mark provider as UNAVAILABLE, fallback to Gemini

**State flow:**
```
HEALTHY ─(failure)─> DEGRADED ─(3 failures)─> UNAVAILABLE
   ▲                                                  │
   └─(success resets counter)──────────────────────┘
```

**See the actual code:**
- Provider factory: [`backend/app/providers/factory.py` (Lines 26-150)](../../backend/app/providers/factory.py)
  - `ProviderStatus` enum (HEALTHY, DEGRADED, UNAVAILABLE)
  - `get_provider()` fallback logic
  - `handle_failure()` and `handle_success()` methods
- Base provider: [`backend/app/providers/base.py` (Lines 37-150)](../../backend/app/providers/base.py)
  - `LLMProvider` abstract interface

**Interview talking point:** "Circuit breaker has 3 states. Prevents hammering dead service."

**Practice question:** "What if both primary and fallback are down?"
**Answer:** "Return 503 Service Unavailable to client. They retry later when service recovers."

---

### 3. LangGraph Supervisor Routing
**Problem:** Orchestrate multi-agent workflow with pauses (human review)

**Solution:** Supervisor decides next agent based on state

**Key insight:**
```python
# When intake draft is complete and human hasn't reviewed yet
if state['phase'] == WorkflowPhase.INTAKE_DRAFT and not state['human_reviewed']:
    return "END"  # ✓ Pause here
    # NOT "human_review" (would cause infinite loop)

# When human approves
if state['human_reviewed']:
    return "migration_planning_agent"  # Resume here
```

**See the actual code:**
- Workflow: [`backend/app/orchestration/workflow.py` (Lines 28-150)](../../backend/app/orchestration/workflow.py)
  - `WorkflowOrchestrator` class
  - `_build_graph()` method that sets up conditional edges
- Supervisor: [`backend/app/orchestration/supervisor.py` (Lines 1-150)](../../backend/app/orchestration/supervisor.py)
  - `Supervisor` class
  - `decide_next_node()` routing logic

**Interview talking point:** "Return 'END' to pause, not recursion. Frontend resumes via API call."

**Practice question:** "What happens if you route back to human_review node?"
**Answer:** "Graph recurses infinitely (GraphRecursionError). Always return 'END' to pause."

---

### 4. Annotated Reducers for State Merging
**Problem:** Two agents update state concurrently → which wins?

**Solution:** Reducers define merge behavior
```python
# Lists: append (concatenate)
normalized_docs: Annotated[List[Dict], merge_lists]

# Dicts: shallow merge
trace_metadata: Annotated[Dict[str, Any], merge_dicts]
```

**Example merge:**
```
Agent A patch: {normalized_docs: [{id: 2}], trace_metadata: {extraction: {...}}}
Agent B patch: {normalized_docs: [{id: 3}], trace_metadata: {questionnaire: {...}}}

Result:
{
  normalized_docs: [{id: 2}, {id: 3}],  # Both appended!
  trace_metadata: {extraction: {...}, questionnaire: {...}}  # Merged!
}
```

**Interview talking point:** "Reducers handle concurrent updates transparently."

**Practice question:** "What if two agents append to normalized_docs simultaneously?"
**Answer:** "Both append succeeds (lists concatenate), no conflict."

---

### 5. Four-Layer Error Recovery
**Problem:** Errors can happen at multiple levels

**Solution:** Each layer handles its responsibility

```
Layer 1: Agent
└─ Try/catch around LLM call
└─ Return error patch (don't throw)

Layer 2: Node
└─ Catch exceptions from agent
└─ Log with traceback
└─ Return error state patch

Layer 3: Supervisor
└─ Check retry_count < max_retries
└─ Route back to same node (retry)
└─ Or route to ERROR phase if exhausted

Layer 4: API
└─ Catch StateTransactionError (version conflict)
└─ Return 409 Conflict (client retries)
└─ Catch other exceptions
└─ Return 500 with error details
```

**Interview talking point:** "Four layers ensure specific recovery strategy per error type."

**Practice question:** "What if LLM times out on 3rd attempt?"
**Answer:** "Agent returns error patch, supervisor sees retry_count==3, routes to ERROR phase instead of retrying."

---

## 📊 Interview Question Breakdown

You'll likely get one of these 7 questions:

| Q | Topic | Key Pattern | Time |
|---|-------|-------------|------|
| 1 | Design workflow state management | Optimistic locking, Annotated reducers | 20 min |
| 2 | Scale to 1000 concurrent workflows | Per-project locks, Redis sharding | 20 min |
| 3 | Fault-tolerant LLM provider system | Circuit breaker, fallback | 20 min |
| 4 | Multi-phase workflow with human review | LangGraph, pause/resume | 15 min |
| 5 | Error recovery strategies | 4-layer recovery | 15 min |
| 6 | Optimize for high throughput | Caching, parallelization, serialization | 20 min |
| 7 | Data consistency & transactions | Write-ahead logging, idempotency | 20 min |

See `SYSTEM-DESIGN-QUESTIONS.md` for complete answers.

---

## 🎤 Your Opening Answer Structure

**When asked: "Design workflow state management..."**

Structure your answer this way:

1. **Problem** (30 seconds)
   - "Multi-agent system needs to update state concurrently"
   - "Risk of lost updates and data inconsistency"

2. **Solution overview** (1 minute)
   - "Use immutable, versioned state with optimistic locking"
   - "Agents propose patches (not direct modification)"
   - "Version checked at commit time"

3. **Design details** (3-5 minutes)
   - State schema with TypedDict
   - Optimistic locking mechanism
   - Annotated reducers for merging
   - Changelog for audit trail

4. **Trade-offs** (1-2 minutes)
   - "Pro: Lock-free reads, scales well"
   - "Con: Must handle retries on conflicts"
   - "Better than pessimistic locking for this workload"

5. **Monitoring** (30 seconds)
   - "Track conflict rate (high = problem)"
   - "Monitor retry frequency"
   - "Alert on state size growth"

---

## ✅ Quick Checklist

Before your interview, confirm:

- [ ] I understand optimistic locking (why version checking works)
- [ ] I can draw circuit breaker state diagram (3 boxes, 3 arrows)
- [ ] I know LangGraph supervisor concept (conditional routing)
- [ ] I understand Annotated reducers (lists append, dicts merge)
- [ ] I can explain 4-layer error recovery
- [ ] I've whiteboarded at least one design
- [ ] I can answer Q1 confidently without looking at notes
- [ ] I know the "why" behind each pattern (not just "how")

---

## 💡 Interview Tips

### Do ✓
- Ask clarifying questions ("How many concurrent users?")
- Draw diagrams (simple is fine)
- Think out loud ("So if this happens... then...")
- Discuss trade-offs (show you understand pros/cons)
- Reference code ("In the codebase, we see...")
- Say "I don't know, but here's how I'd approach it"
- Challenge yourself ("What if that fails?")

### Don't ✗
- Memorize answers (understand the "why")
- Jump to code immediately (design first)
- Get stuck on one detail (move on, come back)
- Say "I don't know" without trying to solve it
- Over-engineer for the constraints given
- Assume perfect conditions (assume failures)

---

## 🚀 Next Steps

1. **Read:** `QUICK-REFERENCE.md` (all 8 patterns)
2. **Study:** `SYSTEM-DESIGN-QUESTIONS.md` → Q1 & Q3
3. **Practice:** Whiteboard your answer using template in `QUICK-REFERENCE.md`
4. **Deep dive:** `TECHNICAL-DEEP-DIVE.md` if you want more detail

---

**You've got this!** 

The patterns here are from production systems. Practice thinking through them, and you'll crush the interview.

*Made with Bob*
