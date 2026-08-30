# Code Reference Guide

**Quick Navigation to Codebase Files**

Use this guide to quickly jump to the actual code files referenced in interview preparation materials.

---

## 🗂️ Core Backend Structure

```
backend/app/
├── main.py                          (Entry point, FastAPI setup)
├── config.py                        (Configuration & settings)
├── orchestration/
│   ├── state.py                     (State schema & reducers)
│   ├── state_manager.py             (Optimistic locking implementation)
│   ├── supervisor.py                (Routing logic)
│   └── workflow.py                  (LangGraph orchestration)
├── providers/
│   ├── base.py                      (Abstract LLMProvider interface)
│   ├── factory.py                   (Circuit breaker factory)
│   ├── openai_provider.py           (OpenAI implementation)
│   └── gemini_provider.py           (Gemini implementation)
├── agents/
│   ├── context_retrieval_agent.py
│   ├── extraction_agent.py
│   ├── questionnaire_agent.py
│   ├── intake_draft_agent.py
│   └── review_validation_agent.py
├── api/
│   ├── orchestration.py             (REST endpoints)
│   ├── documents.py
│   └── projects.py
└── storage/
    ├── redis_client.py              (Redis async client)
    └── qdrant_store.py              (Vector store)
```

---

## 📌 By Interview Pattern

### Pattern 1: Immutable, Versioned State

**Key Files:**

| File | Lines | What's There |
|------|-------|-------------|
| `backend/app/orchestration/state.py` | 1-50 | `merge_lists()` and `merge_dicts()` reducer functions |
| `backend/app/orchestration/state.py` | 49-65 | `WorkflowPhase` enum (all phases) |
| `backend/app/orchestration/state.py` | 82-150 | `MigrationState` TypedDict with all fields |
| `backend/app/orchestration/state.py` | 67-80 | `StateChangelogEntry` structure |
| `backend/app/orchestration/state_manager.py` | 37-70 | `StateManager` class definition |
| `backend/app/orchestration/state_manager.py` | 72-150 | `initialize_state()` method |
| `backend/app/orchestration/state_manager.py` | 150-250 | `commit_state()` method with version checking |

**Study Tip:** Start with `state.py` lines 82-150 to see the full state schema, then jump to `state_manager.py` lines 150-250 to see optimistic locking in action.

---

### Pattern 2: Circuit Breaker for Resilience

**Key Files:**

| File | Lines | What's There |
|------|-------|-------------|
| `backend/app/providers/base.py` | 37-140 | `LLMProvider` abstract base class (interface) |
| `backend/app/providers/base.py` | 12-35 | `ProviderResponse` data model |
| `backend/app/providers/factory.py` | 19-23 | `ProviderStatus` enum (HEALTHY, DEGRADED, UNAVAILABLE) |
| `backend/app/providers/factory.py` | 26-42 | `ProviderFactory` class with health tracking |
| `backend/app/providers/factory.py` | 44-79 | `initialize()` method |
| `backend/app/providers/factory.py` | 107-140 | `get_provider()` fallback logic |
| `backend/app/providers/factory.py` | 142-160 | `handle_provider_failure()` and `handle_provider_success()` |

**Study Tip:** Look at `factory.py` lines 19-23 for state enum, then 107-140 for the actual fallback routing logic.

---

### Pattern 3: LangGraph Orchestration

**Key Files:**

| File | Lines | What's There |
|------|-------|-------------|
| `backend/app/orchestration/workflow.py` | 28-75 | `WorkflowOrchestrator` class initialization |
| `backend/app/orchestration/workflow.py` | 100-200+ | `_build_graph()` method (node additions and edges) |
| `backend/app/orchestration/supervisor.py` | 1-50 | `Supervisor` class definition |
| `backend/app/orchestration/supervisor.py` | 80-150 | `decide_next_node()` routing logic |
| `backend/app/main.py` | 39-81 | Lifespan handler (setup and initialization) |

**Study Tip:** Look at `workflow.py` lines 100-200 to see how nodes are added, then `supervisor.py` lines 80-150 to see routing decisions.

---

### Pattern 4: Annotated Reducers for State Merging

**Key Files:**

| File | Lines | What's There |
|------|-------|-------------|
| `backend/app/orchestration/state.py` | 14-37 | `merge_lists()` reducer implementation |
| `backend/app/orchestration/state.py` | 40-46 | `merge_dicts()` reducer implementation |
| `backend/app/orchestration/state.py` | 110-140 | State fields using `Annotated[Type, reducer]` syntax |

**Study Tip:** Read lines 14-46 to understand reducer functions, then 110-140 to see how they're used in state fields.

---

### Pattern 5: Error Recovery (4-Layer)

**Key Files:**

| File | Lines | What's There |
|------|-------|-------------|
| `backend/app/agents/extraction_agent.py` | 1-100 | Agent-level error handling (Layer 1) |
| `backend/app/orchestration/workflow.py` | 200-300+ | Node wrappers with try/catch (Layer 2) |
| `backend/app/orchestration/supervisor.py` | 100-200+ | Retry logic with retry_count (Layer 3) |
| `backend/app/main.py` | 113-145 | Exception handlers for HTTP layer (Layer 4) |
| `backend/app/orchestration/state_manager.py` | 27-35 | Custom exception definitions |

**Study Tip:** Read layers from bottom up: start with `main.py` 113-145, then `supervisor.py` 100-200, then agent code.

---

### Pattern 6: Performance & Scaling

**Key Files:**

| File | Lines | What's There |
|------|-------|-------------|
| `backend/app/orchestration/state_manager.py` | 55-70 | Per-project lock initialization |
| `backend/app/storage/redis_client.py` | 1-100 | Redis connection pooling & serialization |
| `backend/app/orchestration/workflow.py` | 50-100 | Agent parallelization setup |
| `backend/app/api/orchestration.py` | 1-100 | Request batching patterns |

**Study Tip:** Look at per-project lock pattern, then Redis client for serialization optimization.

---

### Pattern 7: Data Consistency & Transactions

**Key Files:**

| File | Lines | What's There |
|------|-------|-------------|
| `backend/app/orchestration/state_manager.py` | 120-250 | `commit_state()` with atomic writes |
| `backend/app/storage/redis_client.py` | 1-50 | Redis transaction setup |
| `backend/app/orchestration/state.py` | 67-80 | Changelog entry for idempotency |

---

## 🔍 By Study Document

### 00-START-HERE.md → Code References

- Pattern 1: See `state.py` (82-150) + `state_manager.py` (150-250)
- Pattern 2: See `factory.py` (19-150)
- Pattern 3: See `workflow.py` (100-200) + `supervisor.py` (80-150)
- Pattern 4: See `state.py` (14-140)
- Pattern 5: See `main.py` (113-145) + agents code

### QUICK-REFERENCE.md → Code References

- Pattern 1: `state_manager.py` (150-250) - commit_state()
- Pattern 2: `factory.py` (107-140) - get_provider()
- Pattern 3: `workflow.py` (100-200) - _build_graph()
- Pattern 4: `state.py` (14-46) - merge functions
- Pattern 5: `main.py` (113-145) - exception handlers
- Pattern 6: `state_manager.py` (55-70) - per-project locks
- Pattern 7: `state.py` (67-80) - changelog
- Pattern 8: `api/orchestration.py` (250-350) - event_generator()

### SYSTEM-DESIGN-QUESTIONS.md → Code References

**Q1 (State Management):**
- Read: `state.py` (82-150) and `state_manager.py` (120-250)

**Q2 (Scale to 1000):**
- Read: `state_manager.py` (55-70) and `storage/redis_client.py`

**Q3 (Fault-tolerant Providers):**
- Read: `providers/factory.py` (entire file)

**Q4 (Multi-phase with human review):**
- Read: `workflow.py` (100-200) and `supervisor.py` (80-150)

**Q5 (Error Recovery):**
- Read: `main.py` (113-145) and agent files

**Q6 (Performance Optimization):**
- Read: `state_manager.py` (55-70) and `storage/redis_client.py`

**Q7 (Data Consistency):**
- Read: `state_manager.py` (120-250) and `state.py` (67-80)

---

## 🚀 Quick Jump Guide

### Need to understand optimistic locking?
→ `backend/app/orchestration/state_manager.py` lines 150-250

### Need to see circuit breaker implementation?
→ `backend/app/providers/factory.py` lines 107-140

### Need to see LangGraph setup?
→ `backend/app/orchestration/workflow.py` lines 100-200

### Need to see error handling?
→ `backend/app/main.py` lines 113-145

### Need to see state schema?
→ `backend/app/orchestration/state.py` lines 82-150

### Need to see reducer functions?
→ `backend/app/orchestration/state.py` lines 14-46

### Need to see supervisor routing?
→ `backend/app/orchestration/supervisor.py` lines 80-150

---

## 💾 File Sizes & Complexity

| File | Lines | Complexity | Read Time |
|------|-------|-----------|-----------|
| state.py | ~260 | Medium | 15 min |
| state_manager.py | ~400 | High | 25 min |
| factory.py | ~234 | Medium | 15 min |
| workflow.py | ~642 | High | 30 min |
| supervisor.py | ~270 | Medium | 20 min |
| base.py | ~151 | Low | 10 min |
| main.py | ~295 | Medium | 20 min |

---

## 🎓 Recommended Reading Order

**For Quick Understanding (1 hour):**
1. `state.py` (14-46) - Reducers
2. `state.py` (82-100) - State schema basics
3. `factory.py` (19-40) - Circuit breaker states
4. `factory.py` (107-140) - Fallback logic

**For Complete Understanding (3 hours):**
1. `state.py` (entire file)
2. `state_manager.py` (1-100) - Class setup
3. `state_manager.py` (120-250) - Commit logic
4. `factory.py` (entire file)
5. `workflow.py` (100-200) - Graph building
6. `supervisor.py` (80-150) - Routing

**For Production Deep Dive (5+ hours):**
Read all files listed above in order, then explore:
- Agent implementations
- API endpoints
- Storage layer
- Configuration

---

## 📝 How to Use This Guide

1. **In interview preparation:** Reference this guide to jump to actual code
2. **In interviews:** Say "In the codebase at `file.py` line X, we see..."
3. **For learning:** Read the referenced lines to understand implementation details
4. **For verification:** Check code matches concepts in interview materials

---

**Made with Bob**
