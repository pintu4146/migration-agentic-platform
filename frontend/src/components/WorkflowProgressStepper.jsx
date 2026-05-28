/**
 * WorkflowProgressStepper Component
 * 
 * Visual stepper showing workflow phases with completion status
 */

import React from 'react';
import { ProgressIndicator, ProgressStep } from '@carbon/react';
import { getPhaseDisplayName, getPhaseDescription } from '../utils/workflowHelpers';
import './WorkflowProgressStepper.scss';

const WorkflowProgressStepper = ({ currentPhase, completedPhases = [] }) => {
  const phases = [
    { id: 'init', label: 'Initialize' },
    { id: 'context_retrieval', label: 'Retrieve Context' },
    { id: 'extraction', label: 'Extract Facts' },
    { id: 'questionnaire', label: 'Generate Questions' },
    { id: 'intake_draft', label: 'Draft Intake' },
    { id: 'human_review', label: 'Human Review' },
    { id: 'migration_planning', label: 'Plan Migration' },
    { id: 'complete', label: 'Complete' }
  ];

  const getCurrentIndex = () => {
    return phases.findIndex(p => p.id === currentPhase);
  };

  const isPhaseComplete = (phaseId) => {
    return completedPhases.includes(phaseId);
  };

  const isPhaseCurrent = (phaseId) => {
    return currentPhase === phaseId;
  };

  return (
    <div className="workflow-progress-stepper">
      <ProgressIndicator 
        currentIndex={getCurrentIndex()}
        spaceEqually
      >
        {phases.map((phase) => (
          <ProgressStep
            key={phase.id}
            label={phase.label}
            description={getPhaseDescription(phase.id)}
            complete={isPhaseComplete(phase.id)}
            current={isPhaseCurrent(phase.id)}
            invalid={false}
            disabled={false}
          />
        ))}
      </ProgressIndicator>
    </div>
  );
};

export default WorkflowProgressStepper;

// Made with Bob
