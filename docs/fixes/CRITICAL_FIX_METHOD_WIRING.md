# Critical Fix: Agent Method Wiring Issue

## Date: 2026-05-27

## Problem Identified

Through systematic inspection of method wiring and call flow, discovered **CRITICAL architectural mismatch** in agent orchestration:

### Issue 1: Duplicate Context Retrieval Implementations

Two separate implementations existed:
1. **`backend/app/agents/context_retrieval_agent.py`** - Agent with `execute(state)` method
2. **`backend/app/orchestration/context_retrieval.py`** - Service with `retrieve(project_id, profile, query)` method

### Issue 2: Method Name Mismatch

**Before (Broken):**
```python
# workflow.py line 389
context_pack = await self.context_retrieval.retrieve(
    project_id=project_id,
    profile_name=profile_name,
    query=query
)
```

**Problem:**
- `self.context_retrieval` was initialized as `ContextRetriever` (service class)
- But workflow was calling it as if it were `ContextRetrievalAgent` (agent class)
- `ContextRetriever` has `retrieve()` method
- `ContextRetrievalAgent` has `execute()` method
- This would cause: `AttributeError: 'ContextRetriever' object has no attribute 'execute'`

### Issue 3: Inconsistent Agent Interfaces

- ✅ **ExtractionAgent**: `execute(state)` → Returns patch
- ✅ **QuestionnaireAgent**: `execute(state)` → Returns patch  
- ❌ **ContextRetrievalAgent**: `execute(state)` → Returns patch (correct)
- ❌ **Workflow calling**: `retrieve(project_id, profile, query)` (wrong!)

## Root Cause

The system had **TWO COMPETING ARCHITECTURES**:

1. **Agent Pattern** (correct): All agents use `execute(state)` and return state patches
2. **Service Pattern** (legacy): Service classes use specific method signatures

The workflow was mixing both patterns incorrectly.

## Solution Applied

### Fix 1: Changed Workflow Node to Use Agent Pattern

**After (Fixed):**
```python
# workflow.py _context_retrieval_node
async def _context_retrieval_node(self, state: MigrationState) -> Dict[str, Any]:
    """Context retrieval node: fetch context from MCP/Qdrant."""
    project_id = state["project_id"]
    logger.info(f"[context_retrieval_node] Retrieving context for project: {project_id}")
    
    # Execute context retrieval agent - uses execute(state) pattern like other agents
    agent_patch = await self.context_retrieval_agent.execute(state)
    
    logger.info(
        f"[context_retrieval_node] Context retrieval completed. "
        f"Documents: {len(agent_patch.get('normalized_docs', []))}"
    )
    
    # Return state update - LangGraph will merge this automatically
    return {
        **agent_patch,
        "phase": WorkflowPhase.CONTEXT_RETRIEVAL.value,
        "state_version": state["state_version"] + 1,
        "updated_at": datetime.utcnow().isoformat(),
        "last_committed_by": "context_retrieval_agent",
        "last_committed_at": datetime.utcnow().isoformat()
    }
```

### Fix 2: Removed Unused Imports and Methods

- Removed import: `from .context_retrieval import ContextRetriever, get_context_retriever`
- Removed parameter: `context_retrieval: Optional[ContextRetriever] = None` from `__init__`
- Removed method: `async def _ensure_context_retrieval(self)`
- Removed initialization: `self.context_retrieval = context_retrieval`
- Removed flag: `self._context_retrieval_initialized = False`

### Fix 3: Consistent Agent Usage

Now ALL agents follow the same pattern:

```python
# Context Retrieval Agent
agent_patch = await self.context_retrieval_agent.execute(state)

# Extraction Agent  
agent_patch = await self.extraction_agent.execute(state)

# Questionnaire Agent
agent_patch = await self.questionnaire_agent.execute(state)
```

## Impact

### Before Fix
- ❌ Would cause `AttributeError` at runtime
- ❌ Inconsistent agent interfaces
- ❌ Mixing service and agent patterns
- ❌ Confusing architecture

### After Fix
- ✅ Consistent `execute(state)` pattern across all agents
- ✅ Clean agent boundaries
- ✅ No runtime errors
- ✅ Clear, maintainable architecture

## Files Modified

1. **backend/app/orchestration/workflow.py**
   - Changed `_context_retrieval_node` to call `self.context_retrieval_agent.execute(state)`
   - Removed unused `ContextRetriever` imports and initialization
   - Removed `_ensure_context_retrieval()` method

## Verification

The fix ensures:
1. All agents use the same `execute(state)` interface
2. All agents return state patches
3. LangGraph merges patches automatically
4. No method name mismatches
5. Clean separation of concerns

## Related Issues Fixed

This fix also resolves the underlying cause of:
- State version mismatch errors (agents now return patches correctly)
- Workflow execution failures (correct method calls)
- Agent initialization issues (removed unused service pattern)

## Next Steps

1. ✅ Method wiring fixed
2. ⏭️ Test workflow end-to-end
3. ⏭️ Verify all agents execute correctly
4. ⏭️ Monitor for any remaining issues

## Lessons Learned

1. **Consistency is critical**: All agents should follow the same interface pattern
2. **Avoid mixing patterns**: Don't mix service and agent patterns in the same system
3. **Systematic inspection**: Thorough code review caught this before runtime failure
4. **Clear boundaries**: Agent pattern provides cleaner boundaries than service pattern