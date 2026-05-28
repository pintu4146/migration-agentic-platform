# SSE Real-Time Enhancements

## Overview

Enhanced Server-Sent Events (SSE) implementation to provide real-time workflow progress updates with phase transitions and detailed progress information.

## Implementation Summary

### 1. Backend SSE Enhancements

**File:** `backend/app/api/orchestration.py`

#### Changes Made:

1. **Faster Polling (Line 382)**
   - Changed from 1 second to **0.5 seconds** polling interval
   - More responsive to state changes during workflow execution

2. **Phase Transition Detection (Lines 345-350)**
   - Tracks both `state_version` and `phase` changes
   - Sends updates when either changes
   - Detects phase transitions even within the same version

3. **Enriched Event Data (Lines 352-365)**
   ```python
   event_data = {
       "state": state,  # Full state object
       "phase_info": {
           "current_phase": current_phase,
           "version": current_version,
           "timestamp": datetime.utcnow().isoformat(),
           "details": _get_phase_details(state)
       }
   }
   ```

4. **Phase-Specific Details Helper (Lines 314-362)**
   - `_get_phase_details()` function extracts relevant information per phase
   - **context_retrieval**: documents_retrieved, context_source
   - **extraction**: facts_extracted, categories
   - **questionnaire**: questions_generated, high_priority_questions
   - **intake_draft**: draft_created status
   - **human_review**: reviewed status
   - **complete**: plan_generated status

5. **Phase Transition Events (Lines 367-375)**
   - Separate `phase_transition` event type
   - Includes from_phase, to_phase, version, timestamp
   - Logged for debugging

### 2. Frontend SSE Hook Enhancements

**File:** `frontend/src/hooks/useWorkflowSSE.js`

#### Changes Made:

1. **New State Variables (Lines 24-25)**
   ```javascript
   const [phaseInfo, setPhaseInfo] = useState(null);
   const [phaseTransition, setPhaseTransition] = useState(null);
   ```

2. **Enhanced state_update Handler (Lines 64-82)**
   - Parses enriched event data
   - Extracts `state` and `phase_info` separately
   - Backward compatible with old format
   - Logs phase info for debugging

3. **Phase Transition Handler (Lines 84-98)**
   - Listens for `phase_transition` events
   - Updates `phaseTransition` state
   - Auto-clears after 3 seconds for clean UI
   - Logs transitions for debugging

4. **Updated Return Values (Lines 137-144)**
   ```javascript
   return { 
     state, 
     loading, 
     error, 
     isConnected,
     phaseInfo,        // NEW
     phaseTransition,  // NEW
     refetch 
   };
   ```

### 3. UI Enhancements

**File:** `frontend/src/pages/WorkflowExecution.jsx`

#### Changes Made:

1. **Hook Integration (Line 34)**
   ```javascript
   const { state, loading, error: sseError, isConnected, 
           phaseInfo, phaseTransition, refetch } = useWorkflowSSE(projectId);
   ```

2. **Phase Transition Notification (Lines 197-206)**
   - Displays when phase changes
   - Shows "from → to" transition
   - Auto-dismisses after 3 seconds
   - Uses Carbon InlineNotification component

3. **Real-Time Phase Progress Panel (Lines 208-260)**
   - Displays current phase details dynamically
   - Shows phase-specific metrics:
     - **Context Retrieval**: Documents retrieved count
     - **Extraction**: Facts extracted, categories list
     - **Questionnaire**: Questions generated, high priority count
     - **Intake Draft**: Draft creation status
     - **Human Review**: Review status
   - Updates in real-time as workflow progresses

**File:** `frontend/src/pages/WorkflowExecution.scss`

#### Styling Added:

1. **Phase Progress Tile (Lines 85-145)**
   - Gradient background for visual appeal
   - Blue left border for emphasis
   - Grid layout for responsive details display
   - Status badges with color coding:
     - Awaiting: Red background
     - Completed: Green background
     - In Progress: Blue background

2. **Slide-In Animation (Lines 147-159)**
   - Smooth entrance for notifications
   - 0.3s ease-out animation
   - Translates from -10px to 0

## Event Flow

### Before Enhancement
```
User clicks "Execute" 
  ↓
Workflow executes (35 seconds)
  ↓
SSE checks every 1 second
  ↓
Misses intermediate updates
  ↓
Only sees final state
```

### After Enhancement
```
User clicks "Execute"
  ↓
Workflow starts
  ↓
SSE checks every 0.5 seconds
  ↓
Detects phase: init → context_retrieval
  ↓
Sends phase_transition event
  ↓
Sends state_update with details
  ↓
UI shows: "4 documents retrieved"
  ↓
Detects phase: context_retrieval → extraction
  ↓
Sends phase_transition event
  ↓
Sends state_update with details
  ↓
UI shows: "27 facts extracted, 6 categories"
  ↓
... continues for each phase ...
```

## Benefits

### 1. Real-Time Visibility
- Users see progress as it happens
- No more "black box" execution
- Clear indication of what's happening

### 2. Better UX
- Phase transition notifications
- Detailed progress metrics
- Professional, polished feel

### 3. Debugging
- Console logs for every event
- Clear phase transitions
- Timestamp tracking

### 4. Performance
- 2x faster polling (0.5s vs 1s)
- Detects changes immediately
- Minimal overhead

## Testing

### Test Scenario 1: Full Workflow Execution
1. Upload documents
2. Click "Start Workflow"
3. Click "Execute Next Step"
4. **Expected**: See phase transitions in real-time
5. **Expected**: See progress details for each phase

### Test Scenario 2: Phase Details
1. During context_retrieval: See "4 documents retrieved"
2. During extraction: See "27 facts extracted"
3. During questionnaire: See "2 questions generated, 2 high priority"
4. During human_review: See "Status: awaiting_review"

### Test Scenario 3: Notifications
1. Watch for phase transition notifications
2. **Expected**: "Workflow progressed from init to context_retrieval"
3. **Expected**: Notification auto-dismisses after 3 seconds

## Browser Compatibility

- ✅ Chrome/Edge (EventSource native)
- ✅ Firefox (EventSource native)
- ✅ Safari (EventSource native)
- ⚠️ IE11 (Requires polyfill)

## Performance Impact

- **Polling Frequency**: 0.5s (was 1s)
- **Network Overhead**: Minimal (only sends when state changes)
- **Memory**: Negligible (single connection per project)
- **CPU**: Low (simple JSON parsing)

## Future Enhancements

1. **Progress Bars**: Add visual progress bars for each phase
2. **Time Estimates**: Show estimated time remaining
3. **Error Details**: Enhanced error messages with recovery suggestions
4. **Pause/Resume**: Allow users to pause workflow execution
5. **History**: Show timeline of phase transitions

## Rollback Plan

If issues occur:
1. Revert `backend/app/api/orchestration.py` lines 314-382
2. Revert `frontend/src/hooks/useWorkflowSSE.js` lines 24-25, 64-98
3. Revert `frontend/src/pages/WorkflowExecution.jsx` lines 197-260
4. System will fall back to basic SSE (1s polling, no phase details)

## Conclusion

The SSE real-time enhancements provide a significantly improved user experience with:
- ✅ 2x faster state detection
- ✅ Phase transition notifications
- ✅ Detailed progress metrics
- ✅ Professional UI polish
- ✅ Better debugging capabilities

All changes are backward compatible and can be rolled back if needed.