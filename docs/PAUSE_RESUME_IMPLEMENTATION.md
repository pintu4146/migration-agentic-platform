# LangGraph Pause/Resume Implementation Guide

**Date**: 2026-05-29  
**Status**: ✅ Complete and Working  
**Version**: 1.0

---

## Executive Summary

This document explains how the pause/resume mechanism works in our LangGraph-based workflow orchestration system. The implementation uses **stateful checkpointing** with Redis as the state store, providing explicit control over workflow execution flow.

### Key Achievement
✅ **Workflow successfully pauses at human review and can be resumed with updated state**

---

## Architecture Overview

### Pattern: Stateful Checkpointing

Our implementation uses a custom pause/resume pattern that treats **state as the checkpoint**:

```
┌─────────────────────────────────────────────────────────────┐
│                    PAUSE MECHANISM                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. human_review_node sets:                                │
│     - phase: "human_review"                                │
│     - human_reviewed: False                                │
│                                                             │
│  2. Graph routes directly to END                           │
│     graph.add_edge("human_review_node", END)              │
│                                                             │
│  3. astream loop detects pause condition and breaks        │
│     if phase == "human_review" and not human_reviewed:    │
│         break                                              │
│                                                             │
│  4. State saved to Redis                                   │
│     await _sync_state_to_redis(project_id, state)         │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    RESUME MECHANISM                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. API receives resume request                            │
│     POST /api/orchestration/resume                         │
│     { "human_reviewed": true }                             │
│                                                             │
│  2. resume_workflow updates state                          │
│     state["human_reviewed"] = True                         │
│     await state_manager.commit_state(...)                  │
│                                                             │
│  3. Calls execute_workflow with updated state              │
│     return await self.execute_workflow(project_id)         │
│                                                             │
│  4. Supervisor evaluates state and routes                  │
│     if phase == "human_review" and human_reviewed:        │
│         return "migration_planning"                        │
│                                                             │
│  5. Workflow continues from next phase                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Details

### 1. Pause Flow

#### Step 1: Human Review Node
**File**: `backend/app/orchestration/workflow.py:488-503`

```python
async def _human_review_node(self, state: MigrationState) -> Dict[str, Any]:
    """
    Human review node: pause workflow for human review.
    
    This node updates the phase to HUMAN_REVIEW and the workflow ends here.
    The workflow will be resumed later via the API when human_reviewed=True.
    
    Note: This node routes directly to END, not back to supervisor,
    to avoid the recursion issue.
    """
    logger.info(f"[human_review_node] Workflow paused for human review")
    
    # Update phase and metadata
    # The workflow will END after this node (see graph structure)
    return {
        "phase": WorkflowPhase.HUMAN_REVIEW.value,
        "updated_at": datetime.utcnow().isoformat(),
        "last_committed_by": "human_review_gate",
        "last_committed_at": datetime.utcnow().isoformat()
    }
```

**Key Points**:
- Sets `phase: "human_review"`
- Does NOT set `human_reviewed: True` (stays False)
- Returns minimal state update
- No complex logic - just marks the pause point

#### Step 2: Graph Structure
**File**: `backend/app/orchestration/workflow.py:144-163`

```python
# Add edges back to supervisor from each node
# EXCEPT human_review_node which goes directly to END to pause workflow
for node in [
    "context_retrieval_node",
    "extraction_node",
    "questionnaire_node",
    "intake_draft_node",
    "migration_planning_node",
    "validation_node",
    "complete_node"
]:
    graph.add_edge(node, "supervisor")

# Human review node routes directly to END to pause the workflow
# This avoids the recursion issue where supervisor would route back to END
# creating an infinite loop
graph.add_edge("human_review_node", END)
```

**Key Points**:
- Most nodes route back to supervisor for next decision
- `human_review_node` routes directly to END
- This breaks the normal flow and signals a pause
- No supervisor involvement after human review node

#### Step 3: Loop Break Detection
**File**: `backend/app/orchestration/workflow.py:244-280`

```python
async for event in self.workflow.astream(state, config):
    for node_name, node_output in event.items():
        if node_output:
            # Merge node output into state
            final_state = {**final_state, **node_output}
            
            # Sync to Redis for SSE streaming
            await self._sync_state_to_redis(project_id, final_state)
            
            # CRITICAL: Check if we've reached human review phase
            # If so, break the loop to pause the workflow
            if (final_state.get('phase') == WorkflowPhase.HUMAN_REVIEW.value and 
                not final_state.get('human_reviewed', False)):
                logger.info(f"Workflow paused at human review phase for project: {project_id}")
                break
    
    # Break outer loop if we broke inner loop
    if (final_state and 
        final_state.get('phase') == WorkflowPhase.HUMAN_REVIEW.value and 
        not final_state.get('human_reviewed', False)):
        break

logger.info(f"Workflow execution completed for project: {project_id}")
return final_state if final_state else state
```

**Key Points**:
- Explicit check for pause condition
- Breaks both inner and outer loops
- Prevents LangGraph from continuing iteration
- Logs clear pause message

#### Step 4: State Persistence
**File**: `backend/app/orchestration/workflow.py:322-340`

```python
async def _sync_state_to_redis(self, project_id: str, state: Dict[str, Any]) -> None:
    """
    Sync LangGraph state to Redis for SSE streaming.
    
    Args:
        project_id: Project identifier
        state: Current workflow state
    """
    try:
        await self._ensure_state_manager()
        
        # Commit state to Redis
        await self.state_manager.commit_state(
            project_id=project_id,
            patch=state,
            expected_version=state.get("state_version"),
            committed_by="workflow_orchestrator"
        )
    except Exception as e:
        logger.error(f"Failed to sync state to Redis: {e}")
```

**Key Points**:
- State saved to Redis after every node
- Includes all workflow data
- Enables SSE real-time updates
- Provides checkpoint for resume

---

### 2. Resume Flow

#### Step 1: API Endpoint
**File**: `backend/app/api/orchestration.py:192-230`

```python
@router.post("/resume", response_model=ResumeWorkflowResponse)
async def resume_workflow(
    request: ResumeWorkflowRequest
) -> ResumeWorkflowResponse:
    """
    Resume a paused workflow.
    
    Optionally applies state updates (e.g., human review approval).
    """
    try:
        orchestrator = get_workflow_orchestrator()
        
        updated_state = await orchestrator.resume_workflow(
            project_id=request.project_id,
            updates=request.updates
        )
        
        return ResumeWorkflowResponse(
            project_id=updated_state["project_id"],
            state_version=updated_state["state_version"],
            phase=updated_state["phase"],
            message=f"Workflow resumed for project {request.project_id}"
        )
    except Exception as e:
        logger.error(f"Failed to resume workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume workflow: {str(e)}"
        )
```

**Request Example**:
```json
POST /api/orchestration/resume
{
    "project_id": "pintu-test",
    "updates": {
        "human_reviewed": true
    }
}
```

#### Step 2: Resume Workflow Method
**File**: `backend/app/orchestration/workflow.py:283-322`

```python
@trace_operation("workflow_resume", run_type="chain", tags=["workflow", "resume"])
async def resume_workflow(
    self,
    project_id: str,
    updates: Optional[Dict[str, Any]] = None
) -> MigrationState:
    """
    Resume paused workflow.
    
    Args:
        project_id: Project identifier
        updates: Optional state updates (e.g., human review approval)
        
    Returns:
        Updated state
    """
    # Ensure state manager is initialized
    await self._ensure_state_manager()
    
    # Get current state
    state = await self.state_manager.get_state(project_id)
    current_version = state["state_version"]
    
    # Apply updates if provided
    if updates:
        patch = {
            **updates,
            "last_committed_at": datetime.utcnow().isoformat()
        }
        
        state = await self.state_manager.commit_state(
            project_id=project_id,
            patch=patch,
            expected_version=current_version,
            committed_by="human_reviewer"
        )
    
    # Resume execution with updated state
    logger.info(f"Resuming workflow for project: {project_id}")
    return await self.execute_workflow(project_id)
```

**Key Points**:
- Retrieves current state from Redis
- Applies human review updates
- **Calls `execute_workflow` to resume** (this was the missing piece!)
- Returns final state after execution

#### Step 3: Supervisor Routing
**File**: `backend/app/orchestration/supervisor.py:165-176`

```python
elif current_phase == WorkflowPhase.HUMAN_REVIEW:
    if not state.get("human_reviewed"):
        return SupervisorDecision(
            next_node="END",  # Pause workflow for human review
            next_phase=WorkflowPhase.HUMAN_REVIEW,
            reason="Waiting: human review pending"
        )
    return SupervisorDecision(
        next_node="migration_planning",
        next_phase=WorkflowPhase.MIGRATION_PLANNING,
        reason="Review approved: generate migration plan"
    )
```

**Key Points**:
- Supervisor checks `human_reviewed` flag
- If False: routes to END (pause)
- If True: routes to `migration_planning` (continue)
- This is how resume works - supervisor sees updated state and continues

---

## Comparison with LangGraph Built-in Patterns

### Our Custom Pattern (Stateful Checkpointing)

**Advantages**:
- ✅ Explicit control over pause/resume logic
- ✅ State always persisted in Redis (not just in memory)
- ✅ Resume logic is clear and testable
- ✅ No hidden framework magic
- ✅ Works with our existing Redis state management
- ✅ Fully traceable via LangSmith

**Disadvantages**:
- ❌ Requires manual implementation
- ❌ More code to maintain
- ❌ Need to handle edge cases ourselves

### LangGraph `interrupt()` (Official Pattern)

```python
from langgraph.types import interrupt

def human_review_node(state):
    interrupt("human_review_required")  # Saves checkpoint
    return state

# Resume
workflow.invoke(state, config={"thread_id": "same-id"})
```

**Advantages**:
- ✅ Built-in, automatic checkpoint management
- ✅ Less code to write
- ✅ Framework handles edge cases

**Disadvantages**:
- ❌ We couldn't import it (version issue in our setup)
- ❌ Less explicit control
- ❌ Checkpoints might be in-memory only
- ❌ Harder to integrate with Redis state management

### LangGraph `Command` with `goto` (LangGraph 0.2+)

```python
from langgraph.types import Command

def supervisor(state):
    if needs_pause:
        return Command(goto=END)
```

**Advantages**:
- ✅ More declarative
- ✅ Cleaner syntax

**Disadvantages**:
- ❌ Requires newer LangGraph version
- ❌ Still less explicit than our pattern

---

## Why Our Pattern Works

### 1. State is the Source of Truth
- All workflow data stored in Redis
- State includes phase, flags, and all agent outputs
- Resume = start new execution with updated state

### 2. Supervisor is the Router
- Always evaluates current state
- Makes routing decisions based on state flags
- No hidden state transitions

### 3. Explicit Pause/Resume
- Pause: Break loop when condition met
- Resume: Update state + start new execution
- No magic - just clear control flow

### 4. Transaction-Safe Updates
- State versioning prevents conflicts
- Optimistic locking ensures consistency
- Changelog tracks all state changes

---

## Testing the Implementation

### Test Pause

1. **Start workflow**:
```bash
POST /api/orchestration/start
{
    "project_id": "test-project",
    "mcp_profile": "context_retrieval_profile"
}
```

2. **Execute workflow**:
```bash
POST /api/orchestration/execute
{
    "project_id": "test-project"
}
```

3. **Expected logs**:
```
[human_review_node] Workflow paused for human review
Workflow node 'human_review_node' completed, phase: human_review
Workflow paused at human review phase for project: test-project ✅
Workflow execution completed for project: test-project ✅
```

4. **Verify state**:
```bash
GET /api/orchestration/state/test-project
```

Expected response:
```json
{
    "phase": "human_review",
    "human_reviewed": false,
    "state_version": 1
}
```

### Test Resume

1. **Resume workflow**:
```bash
POST /api/orchestration/resume
{
    "project_id": "test-project",
    "updates": {
        "human_reviewed": true
    }
}
```

2. **Expected logs**:
```
Resuming workflow for project: test-project
[supervisor_node] Current phase: human_review, version: 2
[supervisor_node] Decision: next_node=migration_planning
Routing to: migration_planning
```

3. **Verify state**:
```bash
GET /api/orchestration/state/test-project
```

Expected response:
```json
{
    "phase": "migration_planning",
    "human_reviewed": true,
    "state_version": 2
}
```

---

## Common Issues and Solutions

### Issue 1: Recursion Limit Error

**Symptom**:
```
GraphRecursionError: Recursion limit of 25 reached without hitting a stop condition
```

**Cause**:
- `human_review_node` was routing back to supervisor
- Supervisor was routing to END
- Phase wasn't changing, triggering recursion detection

**Solution**:
- Route `human_review_node` directly to END
- Add explicit break in `astream` loop

### Issue 2: Resume Not Working

**Symptom**:
- Resume API returns success but workflow doesn't continue

**Cause**:
- `resume_workflow` method was incomplete
- Missing call to `execute_workflow`

**Solution**:
- Added `return await self.execute_workflow(project_id)` at line 322

### Issue 3: State Not Persisting

**Symptom**:
- State lost after pause

**Cause**:
- Missing `_sync_state_to_redis` call

**Solution**:
- Call `_sync_state_to_redis` after every node execution

---

## Best Practices

### 1. Always Check Pause Conditions
```python
if (state.get('phase') == WorkflowPhase.HUMAN_REVIEW.value and 
    not state.get('human_reviewed', False)):
    break
```

### 2. Log Pause/Resume Events
```python
logger.info(f"Workflow paused at human review phase for project: {project_id}")
logger.info(f"Resuming workflow for project: {project_id}")
```

### 3. Validate State Before Resume
```python
state = await self.state_manager.get_state(project_id)
if state.get('phase') != WorkflowPhase.HUMAN_REVIEW.value:
    raise ValueError("Cannot resume: workflow not at human review phase")
```

### 4. Use State Versioning
```python
current_version = state["state_version"]
state = await self.state_manager.commit_state(
    project_id=project_id,
    patch=updates,
    expected_version=current_version,
    committed_by="human_reviewer"
)
```

---

## Future Enhancements

### 1. Multiple Pause Points
- Add more human review gates
- Support different pause types (approval, input, decision)

### 2. Timeout Handling
- Auto-resume after timeout
- Send notifications for pending reviews

### 3. Rollback Support
- Revert to previous state
- Undo human review decisions

### 4. Audit Trail
- Track all pause/resume events
- Log who approved/rejected

---

## Conclusion

Our stateful checkpointing pattern provides:
- ✅ Explicit control over workflow execution
- ✅ Clear pause/resume semantics
- ✅ Transaction-safe state updates
- ✅ Full traceability via LangSmith
- ✅ Integration with Redis state management

The implementation is production-ready and has been tested successfully with the workflow pausing at human review and resuming to continue to migration planning.

---

## References

- **Workflow Implementation**: `backend/app/orchestration/workflow.py`
- **Supervisor Logic**: `backend/app/orchestration/supervisor.py`
- **API Endpoints**: `backend/app/api/orchestration.py`
- **State Management**: `backend/app/orchestration/state_manager.py`
- **LangGraph Documentation**: https://langchain-ai.github.io/langgraph/

---

**Last Updated**: 2026-05-29  
**Author**: Migration Copilot Team  
**Status**: ✅ Production Ready