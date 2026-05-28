/**
 * ActivityLog Component
 * 
 * Displays real-time activity log with status indicators
 */

import React from 'react';
import { 
  StructuredListWrapper, 
  StructuredListHead,
  StructuredListRow,
  StructuredListCell,
  StructuredListBody,
  Tag
} from '@carbon/react';
import { 
  Checkmark, 
  InProgress, 
  WarningAlt, 
  ErrorFilled,
  Pause
} from '@carbon/icons-react';
import { formatTimestamp } from '../utils/workflowHelpers';
import './ActivityLog.scss';

const ActivityLog = ({ activities = [], isLive = false }) => {
  const getIcon = (status) => {
    switch(status) {
      case 'success':
        return <Checkmark size={20} className="activity-icon success-icon" />;
      case 'in_progress':
        return <InProgress size={20} className="activity-icon progress-icon" />;
      case 'warning':
        return <WarningAlt size={20} className="activity-icon warning-icon" />;
      case 'error':
        return <ErrorFilled size={20} className="activity-icon error-icon" />;
      case 'paused':
        return <Pause size={20} className="activity-icon paused-icon" />;
      default:
        return null;
    }
  };

  const getStatusTag = (status) => {
    const tagTypes = {
      'success': 'green',
      'in_progress': 'blue',
      'warning': 'yellow',
      'error': 'red',
      'paused': 'gray'
    };
    return tagTypes[status] || 'gray';
  };

  if (!activities || activities.length === 0) {
    return (
      <div className="activity-log">
        <div className="activity-log-header">
          <h4>Activity Log</h4>
          {isLive && <Tag type="red" size="sm" className="live-badge">● LIVE</Tag>}
        </div>
        <div className="activity-log-empty">
          <p>No activities yet. Start the workflow to see real-time updates.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="activity-log">
      <div className="activity-log-header">
        <h4>Activity Log</h4>
        {isLive && <Tag type="red" size="sm" className="live-badge">● LIVE</Tag>}
      </div>
      
      <StructuredListWrapper className="activity-list">
        <StructuredListHead>
          <StructuredListRow head>
            <StructuredListCell head>Status</StructuredListCell>
            <StructuredListCell head>Time</StructuredListCell>
            <StructuredListCell head>Activity</StructuredListCell>
            <StructuredListCell head>Phase</StructuredListCell>
          </StructuredListRow>
        </StructuredListHead>
        <StructuredListBody>
          {activities.map((activity, index) => (
            <StructuredListRow key={index} className={`activity-row activity-${activity.status}`}>
              <StructuredListCell className="activity-status-cell">
                {getIcon(activity.status)}
              </StructuredListCell>
              <StructuredListCell className="activity-time-cell">
                {formatTimestamp(activity.timestamp)}
              </StructuredListCell>
              <StructuredListCell className="activity-message-cell">
                {activity.message}
              </StructuredListCell>
              <StructuredListCell className="activity-phase-cell">
                <Tag type={getStatusTag(activity.status)} size="sm">
                  {activity.phase || 'unknown'}
                </Tag>
              </StructuredListCell>
            </StructuredListRow>
          ))}
        </StructuredListBody>
      </StructuredListWrapper>
    </div>
  );
};

export default ActivityLog;

// Made with Bob
