/**
 * PhaseStatusCard Component
 * 
 * Displays summary metrics for completed workflow phases
 */

import React from 'react';
import { Tile } from '@carbon/react';
import './PhaseStatusCard.scss';

const PhaseStatusCard = ({ phase, data }) => {
  if (!data) return null;

  const renderContent = () => {
    switch(phase) {
      case 'context_retrieval':
        return (
          <>
            <h4>Context Retrieved</h4>
            <div className="metric-large">{data.documents_count || 0}</div>
            <div className="metric-label">Documents</div>
            <div className="metric-detail">
              Source: {data.source || 'unknown'}
            </div>
          </>
        );
      
      case 'extraction':
        return (
          <>
            <h4>Facts Extracted</h4>
            <div className="metric-large">{data.facts_count || 0}</div>
            <div className="metric-label">Facts</div>
            <div className="metric-detail">
              Avg Confidence: {data.avg_confidence ? (data.avg_confidence * 100).toFixed(0) : 0}%
            </div>
            {data.categories > 0 && (
              <div className="metric-detail">
                {data.categories} Categories
              </div>
            )}
          </>
        );
      
      case 'questionnaire':
        return (
          <>
            <h4>Questions Generated</h4>
            <div className="metric-large">{data.questions_count || 0}</div>
            <div className="metric-label">Questions</div>
            <div className="metric-detail">
              {data.high_priority_count || 0} High Priority
            </div>
            {data.missing_fields > 0 && (
              <div className="metric-detail">
                {data.missing_fields} Missing Fields
              </div>
            )}
          </>
        );
      
      default:
        return (
          <>
            <h4>{phase}</h4>
            <div className="metric-large">-</div>
            <div className="metric-label">No data</div>
          </>
        );
    }
  };

  return (
    <Tile className="phase-status-card">
      {renderContent()}
    </Tile>
  );
};

export default PhaseStatusCard;

// Made with Bob
