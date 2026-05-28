# Critical Bugs Memory - DO NOT REPEAT THESE MISTAKES

**Purpose**: This file serves as persistent memory for AI coding agents to avoid repeating past mistakes.  
**Last Updated**: 2026-05-28  
**Status**: Application Stable - 10 Critical Bugs Fixed  

---

## 🚨 CRITICAL RULES - READ BEFORE CODING

### Rule #1: NEVER Store datetime Objects in JSON-Serializable State
**Why**: Python datetime objects cannot be JSON serialized.  
**Always**: Use `datetime.utcnow().isoformat()` to convert to ISO 8601 strings.  
**Example**:
```python
# ❌ WRONG - Will cause JSON serialization error
extracted_at=datetime.utcnow()

# ✅ CORRECT - ISO 8601 string
extracted_at=datetime.utcnow().isoformat()
```

### Rule #2: ALWAYS Initialize ALL State Fields
**Why**: Missing fields cause KeyError exceptions.  
**Always**: Check `MigrationState` schema and initialize every field in `create_initial_state()`.  
**Example**:
```python
# ❌ WRONG - Missing gap_analysis
return MigrationState(
    project_id=project_id,
    # gap_analysis missing!
)

# ✅ CORRECT - All fields initialized
return MigrationState(
    project_id=project_id,
    gap_analysis=None,  # Initialize even if None
)
```

### Rule #3: LangGraph Workflow Pausing Requires Explicit Flags
**Why**: Supervisor needs flags to know when to pause workflow.  
**Always**: Set control flags like `human_reviewed=False` when pausing is needed.  
**Example**:
```python
# ❌ WRONG - Supervisor doesn't know to pause
async def _human_review_node(self, state):
    return {
        "phase": WorkflowPhase.HUMAN_REVIEW.value,
        # Missing: human_reviewed flag!
    }

# ✅ CORRECT - Explicit pause signal
async def _human_review_node(self, state):
    return {
        "phase": WorkflowPhase.HUMAN_REVIEW.value,
        "human_reviewed": False,  # Signal supervisor to pause
    }
```

### Rule #4: ALWAYS Strip Markdown from LLM JSON Responses
**Why**: LLMs often wrap JSON in markdown code blocks.  
**Always**: Strip ```json and ``` before parsing.  
**Example**:
```python
# ❌ WRONG - Will fail if LLM returns markdown
result = json.loads(response.text)

# ✅ CORRECT - Strip markdown first
content = response.text
if content.startswith('```'):
    lines = content.split('\n')
    if lines[0].startswith('```'):
        lines = lines[1:]  # Remove opening ```json
    if lines and lines[-1].strip() == '```':
        lines = lines[:-1]  # Remove closing ```
    content = '\n'.join(lines)
result = json.loads(content)
```

### Rule #5: Method Names Must Match Caller Expectations
**Why**: AttributeError if method name doesn't match what's being called.  
**Always**: Verify method names match across workflow and agent classes.  
**Example**:
```python
# ❌ WRONG - Workflow calls retrieve_context() but method is execute()
class ContextRetrievalAgent:
    async def execute(self, state):  # Wrong name!
        pass

# ✅ CORRECT - Method name matches caller
class ContextRetrievalAgent:
    async def retrieve_context(self, state):  # Matches workflow call
        pass
```

---

## 📋 Complete Bug History (10 Bugs Fixed)

### Bug #1: Context Retrieval Method Wiring
**Date**: 2026-05-27  
**Severity**: 🔴 CRITICAL  
**Error**: `AttributeError: 'ContextRetrievalAgent' object has no attribute 'retrieve_context'`  
**Root Cause**: Method named `execute()` but workflow called `retrieve_context()`  
**Fix**: Renamed method to match caller expectations  
**File**: `backend/app/agents/context_retrieval_agent.py`  
**Lesson**: Always verify method names match across classes  

---

### Bug #2: Gemini JSON Markdown Parsing
**Date**: 2026-05-27  
**Severity**: 🔴 CRITICAL  
**Error**: `json.decoder.JSONDecodeError: Expecting value: line 1 column 1`  
**Root Cause**: Gemini returned JSON wrapped in markdown code blocks  
**Fix**: Added markdown stripping logic before JSON parsing  
**File**: `backend/app/providers/gemini_provider.py`  
**Lesson**: LLMs often wrap JSON in markdown - always strip it  

**Code Pattern to Use**:
```python
# Strip markdown code blocks
if content.startswith('```'):
    lines = content.split('\n')
    if lines[0].startswith('```'):
        lines = lines[1:]
    if lines and lines[-1].strip() == '```':
        lines = lines[:-1]
    content = '\n'.join(lines)
```

---

### Bug #3: Missing gap_analysis State Field
**Date**: 2026-05-27  
**Severity**: 🟡 MEDIUM  
**Error**: `KeyError: 'gap_analysis'`  
**Root Cause**: Field defined in schema but not initialized in `create_initial_state()`  
**Fix**: Added `gap_analysis=None` to initial state  
**File**: `backend/app/orchestration/state.py`  
**Lesson**: Every field in TypedDict schema MUST be initialized  

**Checklist**:
- [ ] Check `MigrationState` schema
- [ ] Verify ALL fields are in `create_initial_state()`
- [ ] Initialize even optional fields with None

---

### Bug #4: Human Review Infinite Loop (First Occurrence)
**Date**: 2026-05-27  
**Severity**: 🔴 CRITICAL  
**Error**: `GraphRecursionError: Recursion limit of 25 reached`  
**Root Cause**: `_human_review_node` didn't set `human_reviewed=False`  
**Fix**: Added `human_reviewed=False` to return dict  
**File**: `backend/app/orchestration/workflow.py`  
**Lesson**: Workflow pause requires explicit control flags  

**Pattern**:
```python
# Supervisor checks this flag
if not state.get("human_reviewed"):
    return SupervisorDecision(
        next_node="END",  # Pause workflow
        next_phase=WorkflowPhase.HUMAN_REVIEW,
        reason="Waiting: human review pending"
    )
```

---

### Bug #5: Normalized Docs Population
**Date**: 2026-05-27  
**Severity**: 🟡 MEDIUM  
**Error**: Empty `normalized_docs` field after context retrieval  
**Root Cause**: Agent returned `context_pack` but didn't populate `normalized_docs`  
**Fix**: Added explicit `normalized_docs` population  
**File**: `backend/app/agents/context_retrieval_agent.py`  
**Lesson**: Populate ALL relevant state fields, not just primary ones  

**Pattern**:
```python
return {
    "context_pack": context_pack_dict,
    "normalized_docs": [doc.dict() for doc in context_pack.documents],  # Don't forget!
}
```

---

### Bug #6: Extraction Agent Field Mapping
**Date**: 2026-05-27  
**Severity**: 🟡 MEDIUM  
**Error**: Agent looking for wrong field name in state  
**Root Cause**: Inconsistent field naming between state schema and agent  
**Fix**: Updated agent to use correct field name from schema  
**File**: `backend/app/agents/extraction_agent.py`  
**Lesson**: Always reference state schema for correct field names  

---

### Bug #7: SSE Real-Time Updates (Enhancement)
**Date**: 2026-05-28  
**Severity**: 🟢 ENHANCEMENT  
**Problem**: No real-time updates, users had to refresh manually  
**Solution**: Implemented hybrid SSE architecture  
**Files**: Multiple (workflow.py, orchestration.py, useWorkflowSSE.js)  
**Lesson**: Hybrid approach (LangGraph + Redis + SSE) works well for POC  

**Architecture**:
1. LangGraph `astream()` detects node completions
2. State synced to Redis after each node
3. SSE endpoint polls Redis every 0.5 seconds
4. Frontend receives real-time updates

---

### Bug #8: Redis Datetime Serialization
**Date**: 2026-05-28  
**Severity**: 🔴 CRITICAL  
**Error**: `Object of type datetime is not JSON serializable`  
**Root Cause**: `ContextPack` contained datetime objects  
**Fix**: Changed to `.isoformat()` strings  
**Files**: `backend/app/agents/context_retrieval_agent.py`, `backend/app/storage/redis_client.py`  
**Lesson**: NEVER store datetime objects in JSON-serializable structures  

**Wrong Code**:
```python
extracted_at=datetime.utcnow()  # ❌ datetime object
retrieved_at=datetime.utcnow()  # ❌ datetime object
```

**Correct Code**:
```python
extracted_at=datetime.utcnow().isoformat()  # ✅ ISO string
retrieved_at=datetime.utcnow().isoformat()  # ✅ ISO string
```

**Safety Net** (also implemented):
```python
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)

# Use in json.dumps()
json.dumps(value, cls=DateTimeEncoder)
```

---

### Bug #9: Human Review Loop Regression
**Date**: 2026-05-28  
**Severity**: 🔴 CRITICAL  
**Error**: `GraphRecursionError: Recursion limit of 25 reached` (again!)  
**Root Cause**: Fix from Bug #4 was lost during code changes  
**Fix**: Reapplied `human_reviewed=False` flag  
**File**: `backend/app/orchestration/workflow.py`  
**Lesson**: Critical fixes can regress - need persistent documentation  

**This is why this file exists!**

---

### Bug #10: Questionnaire Text Contrast
**Date**: 2026-05-28  
**Severity**: 🟡 MEDIUM (UX)  
**Problem**: White text on white background - unreadable  
**Root Cause**: Relying on Carbon's default colors without explicit overrides  
**Fix**: Added explicit color values for high contrast  
**File**: `frontend/src/pages/WorkflowExecution.scss`  
**Lesson**: Always use explicit colors for critical UI elements  

**Pattern**:
```scss
.question-item {
  background: #ffffff;  // Explicit white
  color: #161616;       // Explicit dark text
  border: 1px solid #e0e0e0;
  
  strong {
    color: #0f62fe;     // IBM blue
  }
}
```

---

## 🎯 Coding Patterns to ALWAYS Follow

### Pattern #1: State Field Initialization
```python
def create_initial_state(project_id: str) -> MigrationState:
    now = datetime.utcnow().isoformat()  # ✅ ISO string
    
    return MigrationState(
        # Identity
        project_id=project_id,
        state_version=0,
        phase=WorkflowPhase.INIT,
        created_at=now,  # ✅ ISO string
        updated_at=now,  # ✅ ISO string
        
        # Initialize EVERY field, even if None
        context_pack=None,
        normalized_docs=[],
        extracted_facts=None,
        gap_analysis=None,  # ✅ Don't forget!
        missing_questions=[],
        intake_draft=None,
        human_reviewed=False,  # ✅ Control flag
        migration_plan=None,
        # ... ALL fields
    )
```

### Pattern #2: LLM JSON Response Parsing
```python
async def generate_structured(self, prompt: str, schema: Type[BaseModel]):
    response = await self.client.generate_content_async(prompt)
    content = response.text
    
    # ✅ ALWAYS strip markdown
    if content.startswith('```'):
        lines = content.split('\n')
        if lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        content = '\n'.join(lines)
    
    # Now parse
    try:
        result = json.loads(content)
        return schema(**result)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON: {e}")
        raise ValueError(f"Invalid JSON response: {str(e)}")
```

### Pattern #3: Workflow Pause Control
```python
# In node that should pause workflow
async def _human_review_node(self, state: MigrationState):
    return {
        "phase": WorkflowPhase.HUMAN_REVIEW.value,
        "human_reviewed": False,  # ✅ Explicit pause signal
        "state_version": state["state_version"] + 1,
        "updated_at": datetime.utcnow().isoformat(),  # ✅ ISO string
    }

# In supervisor
elif current_phase == WorkflowPhase.HUMAN_REVIEW:
    if not state.get("human_reviewed"):  # ✅ Check flag
        return SupervisorDecision(
            next_node="END",  # ✅ Pause workflow
            next_phase=WorkflowPhase.HUMAN_REVIEW,
            reason="Waiting: human review pending"
        )
```

### Pattern #4: Datetime Handling
```python
# ✅ ALWAYS use .isoformat()
now = datetime.utcnow().isoformat()

# ✅ In data classes
@dataclass
class ContextPack:
    retrieved_at: str  # ✅ String, not datetime
    
# ✅ When creating
context_pack = ContextPack(
    retrieved_at=datetime.utcnow().isoformat()  # ✅ Convert immediately
)

# ✅ Safety net in Redis client
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)
```

### Pattern #5: UI Text Contrast
```scss
// ✅ ALWAYS use explicit colors
.content-area {
  background: #ffffff;  // Explicit white
  color: #161616;       // Explicit dark text (IBM Carbon)
  
  .label {
    color: #525252;     // Explicit gray
  }
  
  .highlight {
    color: #0f62fe;     // Explicit blue
  }
}

// ❌ NEVER rely on defaults
.content-area {
  // No explicit colors - may have poor contrast!
}
```

---

## 🔍 Pre-Commit Checklist

Before committing ANY code, verify:

- [ ] No datetime objects in JSON-serializable structures (use `.isoformat()`)
- [ ] All state fields initialized in `create_initial_state()`
- [ ] LLM JSON responses have markdown stripping
- [ ] Workflow pause nodes set control flags (e.g., `human_reviewed=False`)
- [ ] Method names match caller expectations
- [ ] UI text has explicit colors for contrast
- [ ] Field names match state schema exactly
- [ ] All TypedDict fields are initialized

---

## 📚 Reference Documents

- **Complete Bug History**: `docs/CRITICAL_FIXES_TO_STABLE_STATE.md`
- **Workflow Fixes**: `docs/WORKFLOW_FIXES_SUMMARY.md`
- **SSE Implementation**: `docs/SSE_REALTIME_ENHANCEMENTS.md`
- **Datetime Fix**: `docs/SSE_DATETIME_FIX.md`

---

## 🚀 Current Application Status

**Status**: ✅ STABLE  
**Last Tested**: 2026-05-28  
**Workflow**: Executes end-to-end without errors  
**SSE**: Real-time updates working  
**UI**: Professional, readable, high-contrast  
**State**: Transaction-safe, no data loss  

**Ready for**: Phase 5 - Intake & Review Agents

---

**REMEMBER**: This file exists because bugs #4 and #9 were the SAME bug that regressed. Don't let it happen again!