# Human Review Recursion Fix

**Date**: 2026-05-29  
**Issue**: Workflow hitting recursion limit when at human_review phase  
**Status**: ✅ FIXED

## Problem Description

When the workflow reached the `human_review` phase and the user clicked "Execute Next Step", the workflow would restart from the beginning, creating an infinite loop that hit LangGraph's recursion limit of 25.

### Error Logs
```
2026-05-29 08:10:00 - [human_review_node] Workflow paused for human review
2026-05-29 08:10:00 - Workflow node 'human_review_node' completed, phase: human_review, version: 2
2026-05-29 08:10:00 - Workflow node '__end__' completed, phase: human_review, version: 2
2026-05-29 08:10:00 - [supervisor_node] Current phase: init, version: 1  <-- RESTARTING!
2026-05-29 08:10:00 - ERROR - Recursion limit of 25 reached
```

## Root Cause

The `execute_workflow` method in `workflow.py` was not checking if the workflow was already paused at `human_review` phase. When called again, it would:

1. Get the current state (phase: human_review)
2. Start workflow execution from `__start__`
3. Supervisor would route to `context_retrieval`
4. Workflow would run through all phases again
5. Hit recursion limit after 25 iterations

## Solution

### Backend Fix (workflow.py)

Added a check in `execute_workflow` to prevent re-execution when workflow is paused at human review:

```python
# CRITICAL: Check if workflow is paused at human review
# If so, don't execute - user must use resume_workflow instead
if (state.get('phase') == WorkflowPhase.HUMAN_REVIEW.value and
    not state.get('human_reviewed', False)):
    logger.warning(
        f"Workflow is paused at human review for project {project_id}. "
        f"Use resume_workflow to continue after review."
    )
    raise ValueError(
        "Workflow is paused for human review. "
        "Please approve or reject the review to continue."
    )
```

**Location**: `backend/app/orchestration/workflow.py`, lines 238-248

### Frontend Behavior (Already Correct)

The frontend `WorkflowExecution.jsx` already had the correct logic:
- Shows "Go to Review" button when `phase === 'human_review'`
- Shows "Execute Next Step" button for other phases
- "Go to Review" navigates to `/review/:projectId`

**Location**: `frontend/src/pages/WorkflowExecution.jsx`, lines 177-194

## Workflow Flow

### Correct Flow
1. Workflow executes: init → context_retrieval → extraction → questionnaire → intake_draft → validation → human_review
2. Workflow pauses at human_review (routes to END)
3. User clicks "Go to Review" button
4. User reviews intake draft and validation results
5. User clicks "Approve" or "Reject"
6. Frontend calls `resumeWorkflow` API with review decision
7. Workflow resumes from human_review → migration_planning → complete

### Previous Incorrect Flow (FIXED)
1. Workflow pauses at human_review
2. User clicks "Execute Next Step" (should not be available)
3. `execute_workflow` called again
4. Workflow restarts from init
5. Infinite loop → recursion limit

## Graph Structure

The LangGraph structure correctly routes human_review_node to END:

```python
# Human review node routes directly to END to pause the workflow
# This avoids the recursion issue where supervisor would route back to END
# creating an infinite loop
graph.add_edge("human_review_node", END)
```

**Location**: `backend/app/orchestration/workflow.py`, lines 158-161

## Testing

### Test Case 1: Normal Workflow Execution
✅ Workflow executes from init to human_review and pauses correctly

### Test Case 2: Attempt to Execute at Human Review
✅ Backend returns error: "Workflow is paused for human review"
✅ Frontend shows "Go to Review" button instead of "Execute Next Step"

### Test Case 3: Resume After Review
✅ User approves/rejects review
✅ `resumeWorkflow` API called with review decision
✅ Workflow continues to migration_planning phase

## Files Modified

1. **backend/app/orchestration/workflow.py**
   - Added human_review phase check in `execute_workflow` method
   - Lines 238-248

2. **frontend/src/pages/HumanReview.jsx**
   - Fixed invalid Carbon component imports (Section, Heading)
   - Replaced with standard HTML elements (div, h2)
   - Lines 163-168, 198

## Related Documentation

- [Pause/Resume Implementation](../PAUSE_RESUME_IMPLEMENTATION.md)
- [Phase 5 Completion](../phase-wise/PHASE5_INTAKE_REVIEW_AGENTS.md)
- [Workflow Overview](../workflow/01-workflow-overview.md)

## Prevention

To prevent similar issues in the future:

1. **Always check workflow phase** before executing
2. **Use resume_workflow** for paused workflows, not execute_workflow
3. **Frontend should hide execute button** when workflow is paused
4. **Backend should validate** workflow state before execution
5. **LangGraph edges** should be carefully designed to avoid loops

## Status

✅ **FIXED** - Workflow now correctly pauses at human review and prevents re-execution.

---

**Fixed by**: Bob (AI Assistant)  
**Verified**: 2026-05-29