# 2-Hour Interview Prep Path

**Quick Preparation Guide - Fast Interview Ready**

Do this in the 24 hours before your interview.

---

## ⏱️ Timeline

- **Session 1 (30 min):** Core concepts
- **Session 2 (30 min):** Two key questions
- **Session 3 (30 min):** Quick reference & patterns
- **Session 4 (30 min):** Whiteboarding practice

---

## Session 1: Core Concepts (30 minutes)

### Part A: Immutable, Versioned State (10 min)

**Read:** `00-START-HERE.md` → Section "Immutable, Versioned State"

**Key takeaway:**
```
Agent A reads version 5
Agent B reads version 5
Agent A writes → version becomes 6 ✓
Agent B tries to write → sees version 6, not 5 → fails
Agent B retries with version 6 → succeeds
```

**Talking point:** "Optimistic locking works when reads >> writes (agents read state 100x, update 10x)"

### Part B: Circuit Breaker (10 min)

**Read:** `00-START-HERE.md` → Section "Circuit Breaker for Resilience"

**Key takeaway:**
```
State 1: HEALTHY (use normally)
State 2: DEGRADED (after 1 failure, still use but track)
State 3: UNAVAILABLE (after 3 failures, use fallback)
Recovery: Success resets counter back to HEALTHY
```

**Talking point:** "Prevents cascading failures when service is down"

### Part C: LangGraph & Supervisor (10 min)

**Read:** `00-START-HERE.md` → Section "LangGraph Supervisor Routing"

**Key takeaway:**
```
❌ WRONG: return "human_review"  → infinite loop
✓ RIGHT: return "END"            → pause here
Later: Frontend calls API with human_reviewed=true
✓ RIGHT: return "migration_planning_agent"  → resume
```

**Talking point:** "Return END to pause, not recursion. Frontend resumes via API."

---

## Session 2: Two Key Interview Questions (30 minutes)

### Question 1: Design Workflow State (15 min)

**File:** `SYSTEM-DESIGN-QUESTIONS.md` → Q1

**Read the answer.** Your job is to understand the flow:

1. Problem statement
2. Solution overview (state schema)
3. Optimistic locking mechanism
4. Annotated reducers
5. Trade-offs

**Practice:** Close the document and explain to yourself in 3 minutes.

**Common follow-up:** "What if conflict rate is 50%?"
**Answer:** "Switch to pessimistic locking (hold global lock) since conflicts are frequent."

### Question 2: Fault-Tolerant LLM Providers (15 min)

**File:** `SYSTEM-DESIGN-QUESTIONS.md` → Q3

**Read the answer.** Key sections:

1. Abstract interface (LLMProvider)
2. Factory with circuit breaker
3. Failure modes and recovery
4. Monitoring setup

**Practice:** Close the document and explain the circuit breaker states.

**Common follow-up:** "What if both providers are down?"
**Answer:** "Return 503 Service Unavailable. Frontend shows error, user can retry."

---

## Session 3: Quick Reference & Patterns (30 minutes)

### Part A: 8 Core Patterns (15 min)

**File:** `QUICK-REFERENCE.md`

Read Section "The 8 Core Patterns You Need to Know"

Focus on these 8 (skip code details for now):
1. Optimistic Locking
2. Circuit Breaker
3. LangGraph Supervisor
4. Annotated Reducers
5. Error Recovery Layers
6. Retry with Backoff
7. Dependency Injection
8. SSE Streaming

**Don't memorize code, understand concepts.**

### Part B: Trade-offs Table (10 min)

**File:** `QUICK-REFERENCE.md`

Study the "Trade-offs Decision Table"

This is how you handle: "Why did you choose X over Y?"

Example:
```
Q: Why optimistic locking instead of pessimistic?
A: Optimistic is better for read-heavy (agents read 100x, update 10x).
   Lock-free reads scale better. Only check version at commit time.
   Pro: Scalable. Con: Must handle retries on conflicts.
   Trade-off: We chose scalability over simplicity.
```

### Part C: Decision Flow (5 min)

**File:** `QUICK-REFERENCE.md`

Look at "Decision Table" section — this is your decision framework for interview.

---

## Session 4: Whiteboarding Practice (30 minutes)

### Part A: Whiteboard Template (10 min)

**File:** `QUICK-REFERENCE.md`

Study the "Whiteboard Template" section.

This is your structure:

```
1. PROBLEM (what are we solving?)
2. CONSTRAINTS (throughput? latency? users?)
3. HIGH LEVEL (boxes, arrows)
4. DEEP DIVE: Specific pattern
5. DEEP DIVE: Resilience
6. SCALE: How to handle 1000x?
7. MONITORING: What to track?
```

### Part B: Practice with Q1 (20 min)

Question: "Design workflow state management"

**Your turn now.**

1. Open a blank whiteboard (real or digital)
2. Set timer for 15 minutes
3. Follow the template above
4. Draw boxes and arrows
5. Write key concepts

Do NOT look at the answer file!

**When done:** Compare with `SYSTEM-DESIGN-QUESTIONS.md` → Q1

---

## Your Cheat Sheet for Interview Day

Print or memorize these:

### Three Patterns to Reference
1. **Optimistic Locking:** "Version checking at commit time"
2. **Circuit Breaker:** "HEALTHY → DEGRADED → UNAVAILABLE states"
3. **LangGraph:** "Supervisor routes agents based on state"

### Key Numbers
- Failures to mark UNAVAILABLE: 3
- Backoff times: 2s, 4s, 8s
- Checkpoint interval: Every 5 commits
- Lock timeout: 10 seconds

### Talking Points
- "Trade-off: _____ vs _____ — we chose _____ because _____"
- "At scale, we would _____"
- "To monitor this, we'd track _____"
- "If that fails, we _____"

---

## Quick Checkup

Before interview, verify:

- [ ] I can explain optimistic locking in 1 minute
- [ ] I can draw circuit breaker (3 states, 3 transitions)
- [ ] I understand LangGraph (supervisor decides next node)
- [ ] I know Annotated reducers (lists append, dicts merge)
- [ ] I can describe 4-layer error recovery
- [ ] I've whiteboarded Q1 once
- [ ] I've answered Q3 out loud
- [ ] I'm not trying to memorize, just understand

---

## Emergency: 30 Minutes to Interview

If you only have 30 minutes:

1. Read `00-START-HERE.md` (15 min)
2. Read `QUICK-REFERENCE.md` → Patterns 1, 2, 3 (15 min)

Focus on:
- Optimistic locking concept
- Circuit breaker states
- LangGraph pause/resume

You'll have the basics. That's often enough.

---

**Good luck! You're prepared.** 🚀

*Made with Bob*
