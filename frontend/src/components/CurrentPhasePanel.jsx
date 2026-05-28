/**
 * CurrentPhasePanel Component
 * 
 * Displays the current workflow phase with status badge and description
 */

import React from 'react';
import { Tile, Tag } from '@carbon/react';
import { 
  CheckmarkFilled, 
  ErrorFilled, 
  InProgress, 
  PauseFilled 
} from '@carbon/icons-react';
import './CurrentPhasePanel.scss';

const CurrentPhasePanel = ({ phase, status }) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'completed':
        return {
          type: 'green',
          icon: CheckmarkFilled,
          label: 'Completed'
        };
      case 'error':
        return {
          type: 'red',
          icon: ErrorFilled,
          label: 'Error'
        };
      case 'paused':
        return {
          type: 'purple',
          icon: PauseFilled,
          label: 'Paused - Review Required'
        };
      case 'in_progress':
      default:
        return {
          type: 'blue',
          icon: InProgress,
          label: 'In Progress'
        };
    }
  };

  const getPhaseDescription = () => {
    const descriptions = {
      init: 'Initializing workflow and preparing environment',
      context_retrieval: 'Fetching context from MCP sources and uploaded documents',
      extraction: 'Extracting technical facts, dependencies, and architecture details',
      questionnaire: 'Analyzing gaps and generating clarification questions',
      intake_draft: 'Drafting comprehensive intake document',
      human_review: 'Waiting for human review and approval',
      migration_planning: 'Generating migration strategy and cloud recommendations',
      complete: 'Workflow completed successfully'
    };
    return descriptions[phase] || 'Processing...';
  };

  const statusConfig = getStatusConfig();
  const StatusIcon = statusConfig.icon;

  return (
    <Tile className="current-phase-panel">
      <div className="phase-header">
        <h3>Current Phase</h3>
        <Tag type={statusConfig.type} renderIcon={StatusIcon}>
          {statusConfig.label}
        </Tag>
      </div>
      
      <div className="phase-content">
        <h2 className="phase-name">
          {phase.split('_').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
          ).join(' ')}
        </h2>
        <p className="phase-description">
          {getPhaseDescription()}
        </p>
      </div>
    </Tile>
  );
};

export default CurrentPhasePanel;

// Made with Bob
