# Minimal Functional UI Improvement Plan
## Focus: Workflow Stage Visibility & Real-Time Processing

**Version**: 1.0  
**Date**: 2026-05-28  
**Priority**: High - Immediate Implementation  
**Scope**: Minimal, Functional, Production-Ready

---

## Executive Summary

This plan focuses on **essential UI improvements** to make workflow execution **visible, understandable, and actionable**. We prioritize showing users what's happening in real-time over complex features.

**Core Principle**: Users should always know:
1. What stage the workflow is in
2. What's currently processing
3. What's been completed
4. What's next
5. If there are any errors

---

## Current Pain Points (Priority Order)

1. ❌ **No visibility during workflow execution** - Users see nothing while workflow runs
2. ❌ **No progress indication** - Can't tell if system is working or stuck
3. ❌ **No stage tracking** - Don't know which phase is active
4. ❌ **No error visibility** - Errors hidden in console
5. ❌ **No results display** - Can't see extracted facts or questions

---

## Minimal Viable Improvements

### Priority 1: Workflow Progress Indicator (CRITICAL)

**What**: Visual stepper showing workflow phases with real-time updates

**Why**: Users need to see the workflow is progressing

**Implementation**:

```jsx
// WorkflowProgressStepper.jsx
import { ProgressIndicator, ProgressStep } from '@carbon/react';

const WorkflowProgressStepper = ({ currentPhase, completedPhases }) => {
  const phases = [
    { id: 'init', label: 'Initialize', description: 'Starting workflow' },
    { id: 'context_retrieval', label: 'Retrieve Context', description: 'Fetching documents' },
    { id: 'extraction', label: 'Extract Facts', description: 'Analyzing content' },
    { id: 'questionnaire', label: 'Generate Questions', description: 'Identifying gaps' },
    { id: 'intake_draft', label: 'Draft Intake', description: 'Creating document' },
    { id: 'human_review', label: 'Human Review', description: 'Awaiting approval' },
    { id: 'migration_planning', label: 'Plan Migration', description: 'Generating plan' },
    { id: 'complete', label: 'Complete', description: 'Workflow finished' }
  ];

  return (
    <ProgressIndicator currentIndex={getCurrentIndex(currentPhase, phases)}>
      {phases.map((phase, index) => (
        <ProgressStep
          key={phase.id}
          label={phase.label}
          description={phase.description}
          complete={completedPhases.includes(phase.id)}
          current={currentPhase === phase.id}
          invalid={false}
        />
      ))}
    </ProgressIndicator>
  );
};
```

**Visual Design**:
```
┌─────────────────────────────────────────────────────────────┐
│ Workflow Progress                                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ✅ Initialize ──> ✅ Retrieve ──> ✅ Extract ──>            │
│                                                               │
│  ✅ Questions ──> ⏸️ Review ──> ⏳ Planning ──> ⏳ Complete   │
│                      ▲                                        │
│                   Current                                     │
│                                                               │
│  Status: Paused - Awaiting Human Review                      │
│  Duration: 53 seconds                                         │
└─────────────────────────────────────────────────────────────┘
```

---

### Priority 2: Live Activity Log (CRITICAL)

**What**: Real-time log showing what's happening

**Why**: Users need to see the system is working

**Implementation**:

```jsx
// ActivityLog.jsx
import { StructuredListWrapper, StructuredListBody, StructuredListRow, StructuredListCell } from '@carbon/react';
import { Checkmark, InProgress, Warning, Error } from '@carbon/icons-react';

const ActivityLog = ({ activities, isLive = false }) => {
  const getIcon = (status) => {
    switch(status) {
      case 'success': return <Checkmark size={16} className="success-icon" />;
      case 'in_progress': return <InProgress size={16} className="progress-icon" />;
      case 'warning': return <Warning size={16} className="warning-icon" />;
      case 'error': return <Error size={16} className="error-icon" />;
      default: return null;
    }
  };

  return (
    <div className="activity-log">
      <h4>Activity Log {isLive && <span className="live-badge">● LIVE</span>}</h4>
      <StructuredListWrapper>
        <StructuredListBody>
          {activities.map((activity, index) => (
            <StructuredListRow key={index}>
              <StructuredListCell>{getIcon(activity.status)}</StructuredListCell>
              <StructuredListCell>{activity.timestamp}</StructuredListCell>
              <StructuredListCell>{activity.message}</StructuredListCell>
            </StructuredListRow>
          ))}
        </StructuredListBody>
      </StructuredListWrapper>
    </div>
  );
};
```

**Visual Design**:
```
┌─────────────────────────────────────────────────────────────┐
│ Activity Log                                        ● LIVE   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ⏸️  14:53:07  Workflow paused for human review             │
│  ✅  14:53:07  Intake draft created successfully            │
│  ✅  14:53:07  Generated 2 high-priority questions          │
│  ✅  14:53:00  Extracted 32 facts (98% confidence)          │
│  ✅  14:52:24  Retrieved 1 document from Qdrant             │
│  ⚠️  14:52:20  MCP returned no documents                    │
│  ℹ️  14:52:19  Starting context retrieval                   │
│  ℹ️  14:52:14  Workflow started for project: pintu-test    │
│                                                               │
│  [Auto-scroll] [Export Log]                                 │
└─────────────────────────────────────────────────────────────┘
```

---

### Priority 3: Phase Status Cards (HIGH)

**What**: Summary cards showing key metrics for each completed phase

**Why**: Users need quick insights into what was accomplished

**Implementation**:

```jsx
// PhaseStatusCard.jsx
import { Tile } from '@carbon/react';

const PhaseStatusCard = ({ phase, data }) => {
  const renderContent = () => {
    switch(phase) {
      case 'context_retrieval':
        return (
          <>
            <h4>Context Retrieved</h4>
            <div className="metric-large">{data.documents_count}</div>
            <div className="metric-label">Documents</div>
            <div className="metric-detail">Source: {data.source}</div>
          </>
        );
      
      case 'extraction':
        return (
          <>
            <h4>Facts Extracted</h4>
            <div className="metric-large">{data.facts_count}</div>
            <div className="metric-label">Facts</div>
            <div className="metric-detail">
              Avg Confidence: {(data.avg_confidence * 100).toFixed(0)}%
            </div>
          </>
        );
      
      case 'questionnaire':
        return (
          <>
            <h4>Questions Generated</h4>
            <div className="metric-large">{data.questions_count}</div>
            <div className="metric-label">Questions</div>
            <div className="metric-detail">
              {data.high_priority_count} High Priority
            </div>
          </>
        );
      
      default:
        return null;
    }
  };

  return (
    <Tile className="phase-status-card">
      {renderContent()}
    </Tile>
  );
};
```

**Visual Design**:
```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ Context      │  │ Facts        │  │ Questions    │
│ Retrieved    │  │ Extracted    │  │ Generated    │
│              │  │              │  │              │
│      1       │  │     32       │  │      2       │
│  Documents   │  │   Facts      │  │  Questions   │
│              │  │              │  │              │
│ Source:      │  │ Confidence:  │  │ High Priority│
│ Qdrant       │  │ 98%          │  │ 2 items      │
└──────────────┘  └──────────────┘  └──────────────┘
```

---

### Priority 4: Current Phase Detail Panel (HIGH)

**What**: Expandable panel showing details of current phase

**Why**: Users need context about what's happening now

**Implementation**:

```jsx
// CurrentPhasePanel.jsx
import { Accordion, AccordionItem } from '@carbon/react';

const CurrentPhasePanel = ({ phase, data, status }) => {
  const getPhaseDescription = () => {
    const descriptions = {
      'context_retrieval': 'Fetching documents from MCP and Qdrant vector store',
      'extraction': 'Using AI to extract technical facts from documents',
      'questionnaire': 'Analyzing gaps and generating clarifying questions',
      'intake_draft': 'Creating structured intake document',
      'human_review': 'Waiting for human review and approval',
      'migration_planning': 'Generating migration strategy and recommendations'
    };
    return descriptions[phase] || 'Processing...';
  };

  const getStatusBadge = () => {
    const badges = {
      'in_progress': { text: 'In Progress', color: 'blue' },
      'paused': { text: 'Paused', color: 'yellow' },
      'completed': { text: 'Completed', color: 'green' },
      'error': { text: 'Error', color: 'red' }
    };
    const badge = badges[status] || badges['in_progress'];
    return <span className={`status-badge status-${badge.color}`}>{badge.text}</span>;
  };

  return (
    <div className="current-phase-panel">
      <div className="phase-header">
        <h3>Current Phase: {phase.replace('_', ' ').toUpperCase()}</h3>
        {getStatusBadge()}
      </div>
      
      <p className="phase-description">{getPhaseDescription()}</p>
      
      {data && (
        <Accordion>
          <AccordionItem title="Phase Details">
            <pre>{JSON.stringify(data, null, 2)}</pre>
          </AccordionItem>
        </Accordion>
      )}
    </div>
  );
};
```

**Visual Design**:
```
┌─────────────────────────────────────────────────────────────┐
│ Current Phase: HUMAN REVIEW                    ⏸️ Paused    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ Waiting for human review and approval of the intake         │
│ document before proceeding to migration planning.            │
│                                                               │
│ ▼ Phase Details                                              │
│   • Intake draft created: Yes                                │
│   • Questions generated: 2                                   │
│   • Review required: Yes                                     │
│   • Next action: Review intake document                      │
│                                                               │
│ [Go to Review Screen]                                        │
└─────────────────────────────────────────────────────────────┘
```

---

### Priority 5: Polling for State Updates (CRITICAL)

**What**: Poll backend every 2 seconds for workflow state updates

**Why**: Keep UI in sync with backend without WebSockets

**Implementation**:

```javascript
// useWorkflowPolling.js
import { useState, useEffect, useCallback } from 'react';
import { getWorkflowState } from '../services/api';

export const useWorkflowPolling = (projectId, isActive = true) => {
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchState = useCallback(async () => {
    if (!projectId || !isActive) return;
    
    try {
      const response = await getWorkflowState(projectId);
      setState(response.data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [projectId, isActive]);

  useEffect(() => {
    // Initial fetch
    fetchState();

    // Poll every 2 seconds if active
    if (isActive) {
      const interval = setInterval(fetchState, 2000);
      return () => clearInterval(interval);
    }
  }, [fetchState, isActive]);

  return { state, loading, error, refetch: fetchState };
};
```

**Usage**:
```jsx
// WorkflowExecution.jsx
const WorkflowExecution = ({ projectId }) => {
  const { state, loading, error } = useWorkflowPolling(projectId, true);

  if (loading) return <Loading />;
  if (error) return <ErrorState message={error} />;

  return (
    <div>
      <WorkflowProgressStepper 
        currentPhase={state.phase}
        completedPhases={getCompletedPhases(state)}
      />
      <CurrentPhasePanel 
        phase={state.phase}
        data={state.trace_metadata}
        status={getPhaseStatus(state)}
      />
      <ActivityLog activities={buildActivityLog(state)} isLive={true} />
    </div>
  );
};
```

---

## Enhanced WorkflowExecution Screen

**Complete Implementation**:

```jsx
// WorkflowExecution.jsx (Enhanced)
import React, { useState } from 'react';
import { 
  Button, 
  InlineLoading,
  InlineNotification,
  Grid,
  Column
} from '@carbon/react';
import { Renew, Stop } from '@carbon/icons-react';
import WorkflowProgressStepper from '../components/WorkflowProgressStepper';
import ActivityLog from '../components/ActivityLog';
import PhaseStatusCard from '../components/PhaseStatusCard';
import CurrentPhasePanel from '../components/CurrentPhasePanel';
import { useWorkflowPolling } from '../hooks/useWorkflowPolling';
import { executeWorkflow, pauseWorkflow } from '../services/api';
import './WorkflowExecution.scss';

const WorkflowExecution = ({ projectId }) => {
  const [isExecuting, setIsExecuting] = useState(false);
  const { state, loading, error, refetch } = useWorkflowPolling(
    projectId, 
    isExecuting
  );

  const handleStartWorkflow = async () => {
    setIsExecuting(true);
    try {
      await executeWorkflow(projectId);
      refetch();
    } catch (err) {
      console.error('Failed to start workflow:', err);
    }
  };

  const handlePauseWorkflow = async () => {
    try {
      await pauseWorkflow(projectId);
      setIsExecuting(false);
      refetch();
    } catch (err) {
      console.error('Failed to pause workflow:', err);
    }
  };

  if (loading && !state) {
    return <InlineLoading description="Loading workflow state..." />;
  }

  if (error) {
    return (
      <InlineNotification
        kind="error"
        title="Error"
        subtitle={error}
        onCloseButtonClick={() => window.location.reload()}
      />
    );
  }

  const completedPhases = getCompletedPhases(state);
  const activities = buildActivityLog(state);
  const phaseData = extractPhaseData(state);

  return (
    <div className="workflow-execution">
      {/* Header */}
      <div className="workflow-header">
        <h2>Workflow Execution: {projectId}</h2>
        <div className="workflow-actions">
          {!isExecuting && state?.phase !== 'complete' && (
            <Button
              kind="primary"
              renderIcon={Renew}
              onClick={handleStartWorkflow}
            >
              Start Workflow
            </Button>
          )}
          {isExecuting && (
            <Button
              kind="danger"
              renderIcon={Stop}
              onClick={handlePauseWorkflow}
            >
              Pause Workflow
            </Button>
          )}
        </div>
      </div>

      {/* Progress Stepper */}
      <div className="workflow-progress">
        <WorkflowProgressStepper
          currentPhase={state?.phase}
          completedPhases={completedPhases}
        />
      </div>

      {/* Phase Status Cards */}
      <Grid className="phase-status-grid">
        <Column lg={4} md={4} sm={4}>
          <PhaseStatusCard phase="context_retrieval" data={phaseData.context} />
        </Column>
        <Column lg={4} md={4} sm={4}>
          <PhaseStatusCard phase="extraction" data={phaseData.extraction} />
        </Column>
        <Column lg={4} md={4} sm={4}>
          <PhaseStatusCard phase="questionnaire" data={phaseData.questionnaire} />
        </Column>
      </Grid>

      {/* Current Phase Detail */}
      <CurrentPhasePanel
        phase={state?.phase}
        data={state?.trace_metadata}
        status={getPhaseStatus(state)}
      />

      {/* Activity Log */}
      <ActivityLog activities={activities} isLive={isExecuting} />
    </div>
  );
};

export default WorkflowExecution;
```

---

## Helper Functions

```javascript
// workflowHelpers.js

export const getCompletedPhases = (state) => {
  if (!state) return [];
  
  const phaseOrder = [
    'init',
    'context_retrieval',
    'extraction',
    'questionnaire',
    'intake_draft',
    'human_review',
    'migration_planning',
    'complete'
  ];
  
  const currentIndex = phaseOrder.indexOf(state.phase);
  return phaseOrder.slice(0, currentIndex);
};

export const getPhaseStatus = (state) => {
  if (!state) return 'unknown';
  
  if (state.phase === 'complete') return 'completed';
  if (state.phase === 'human_review' && !state.human_reviewed) return 'paused';
  if (state.phase === 'error') return 'error';
  return 'in_progress';
};

export const buildActivityLog = (state) => {
  if (!state?.trace_metadata) return [];
  
  const activities = [];
  const metadata = state.trace_metadata;
  
  // Add activities from trace metadata
  if (metadata.context_retrieval) {
    activities.push({
      timestamp: metadata.context_retrieval.timestamp,
      message: `Retrieved ${metadata.context_retrieval.documents_retrieved} documents from ${metadata.context_retrieval.source_used}`,
      status: 'success'
    });
  }
  
  if (metadata.extraction) {
    activities.push({
      timestamp: metadata.extraction.timestamp,
      message: `Extracted ${metadata.extraction.facts_extracted} facts (${(metadata.extraction.avg_confidence * 100).toFixed(0)}% confidence)`,
      status: 'success'
    });
  }
  
  if (metadata.questionnaire) {
    activities.push({
      timestamp: metadata.questionnaire.timestamp,
      message: `Generated ${metadata.questionnaire.questions_generated} questions (${metadata.questionnaire.high_priority_count} high priority)`,
      status: 'success'
    });
  }
  
  // Add current phase status
  if (state.phase === 'human_review' && !state.human_reviewed) {
    activities.push({
      timestamp: new Date().toISOString(),
      message: 'Workflow paused for human review',
      status: 'in_progress'
    });
  }
  
  return activities.reverse(); // Most recent first
};

export const extractPhaseData = (state) => {
  if (!state?.trace_metadata) return {};
  
  return {
    context: {
      documents_count: state.trace_metadata.context_retrieval?.documents_retrieved || 0,
      source: state.trace_metadata.context_retrieval?.source_used || 'unknown'
    },
    extraction: {
      facts_count: state.trace_metadata.extraction?.facts_extracted || 0,
      avg_confidence: state.trace_metadata.extraction?.avg_confidence || 0
    },
    questionnaire: {
      questions_count: state.trace_metadata.questionnaire?.questions_generated || 0,
      high_priority_count: state.trace_metadata.questionnaire?.high_priority_count || 0
    }
  };
};
```

---

## Styling (SCSS)

```scss
// WorkflowExecution.scss

.workflow-execution {
  padding: 2rem;
  
  .workflow-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
    
    h2 {
      margin: 0;
    }
  }
  
  .workflow-progress {
    margin-bottom: 2rem;
    padding: 1.5rem;
    background: var(--cds-ui-01);
    border-radius: 4px;
  }
  
  .phase-status-grid {
    margin-bottom: 2rem;
  }
  
  .phase-status-card {
    text-align: center;
    padding: 1.5rem;
    
    h4 {
      margin-bottom: 1rem;
      font-size: 0.875rem;
      color: var(--cds-text-02);
    }
    
    .metric-large {
      font-size: 3rem;
      font-weight: 600;
      color: var(--cds-text-01);
      line-height: 1;
    }
    
    .metric-label {
      font-size: 0.875rem;
      color: var(--cds-text-02);
      margin-top: 0.5rem;
    }
    
    .metric-detail {
      font-size: 0.75rem;
      color: var(--cds-text-03);
      margin-top: 0.5rem;
    }
  }
  
  .current-phase-panel {
    margin-bottom: 2rem;
    padding: 1.5rem;
    background: var(--cds-ui-01);
    border-radius: 4px;
    
    .phase-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1rem;
      
      h3 {
        margin: 0;
      }
    }
    
    .status-badge {
      padding: 0.25rem 0.75rem;
      border-radius: 12px;
      font-size: 0.75rem;
      font-weight: 600;
      
      &.status-blue {
        background: var(--cds-support-info);
        color: white;
      }
      
      &.status-yellow {
        background: var(--cds-support-warning);
        color: black;
      }
      
      &.status-green {
        background: var(--cds-support-success);
        color: white;
      }
      
      &.status-red {
        background: var(--cds-support-error);
        color: white;
      }
    }
    
    .phase-description {
      color: var(--cds-text-02);
      margin-bottom: 1rem;
    }
  }
  
  .activity-log {
    padding: 1.5rem;
    background: var(--cds-ui-01);
    border-radius: 4px;
    
    h4 {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 1rem;
      
      .live-badge {
        color: var(--cds-support-error);
        font-size: 0.75rem;
        animation: pulse 2s infinite;
      }
    }
    
    .success-icon {
      color: var(--cds-support-success);
    }
    
    .progress-icon {
      color: var(--cds-support-info);
      animation: spin 1s linear infinite;
    }
    
    .warning-icon {
      color: var(--cds-support-warning);
    }
    
    .error-icon {
      color: var(--cds-support-error);
    }
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
```

---

## Implementation Timeline

### Week 1: Core Components (5 days)
- **Day 1**: WorkflowProgressStepper component
- **Day 2**: ActivityLog component
- **Day 3**: PhaseStatusCard component
- **Day 4**: CurrentPhasePanel component
- **Day 5**: Polling hook and integration

### Week 2: Integration & Polish (3 days)
- **Day 1**: Integrate all components into WorkflowExecution screen
- **Day 2**: Add styling and animations
- **Day 3**: Testing and bug fixes

**Total**: 8 days

---

## Success Criteria

✅ **User can see workflow progress in real-time**  
✅ **User knows which phase is currently active**  
✅ **User can see what's been completed**  
✅ **User can see activity log with timestamps**  
✅ **User can see key metrics for each phase**  
✅ **UI updates automatically without refresh**  
✅ **Errors are visible and actionable**  
✅ **Loading states are clear**

---

## What We're NOT Doing (Out of Scope)

❌ WebSocket implementation (using polling instead)  
❌ Complex data visualizations (keeping it simple)  
❌ Detailed fact viewer (Phase 2)  
❌ Question answering interface (Phase 2)  
❌ Intake review interface (Phase 2)  
❌ Migration plan viewer (Phase 2)  
❌ Export functionality (Phase 2)  
❌ Advanced filtering (Phase 2)

---

## Next Steps After This Plan

1. **Implement Priority 1-5** (this plan)
2. **Test with real workflow execution**
3. **Gather user feedback**
4. **Plan Phase 2 enhancements** based on feedback

---

## API Requirements

The backend must provide:

```typescript
// GET /api/orchestration/state/{project_id}
interface WorkflowState {
  project_id: string;
  phase: string;
  state_version: number;
  trace_metadata: {
    context_retrieval?: {
      documents_retrieved: number;
      source_used: string;
      timestamp: string;
    };
    extraction?: {
      facts_extracted: number;
      avg_confidence: number;
      timestamp: string;
    };
    questionnaire?: {
      questions_generated: number;
      high_priority_count: number;
      timestamp: string;
    };
  };
  human_reviewed: boolean;
  // ... other fields
}
```

---

## Conclusion

This plan focuses on **essential, functional improvements** that make workflow execution **visible and understandable**. By implementing these 5 priorities, users will have complete visibility into what's happening during workflow execution.

**Key Benefits**:
- ✅ Minimal implementation effort (8 days)
- ✅ Maximum user value (visibility & feedback)
- ✅ Production-ready quality
- ✅ Foundation for future enhancements

---

**Document Version**: 1.0  
**Last Updated**: 2026-05-28  
**Status**: Ready for Implementation  
**Estimated Effort**: 8 days