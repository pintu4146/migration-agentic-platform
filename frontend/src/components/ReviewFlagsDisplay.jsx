import React from 'react';
import {
  Tag,
  Tile,
  Section,
  Heading
} from '@carbon/react';
import { WarningAlt, Error, Information, Checkmark } from '@carbon/icons-react';
import './ReviewFlagsDisplay.scss';

/**
 * ReviewFlagsDisplay Component
 * 
 * Displays review flags that require human attention:
 * - Critical issues
 * - Warnings
 * - Information items
 * - Validation status
 * 
 * Used in the human review phase to highlight items needing attention.
 */
const ReviewFlagsDisplay = ({ reviewFlags, validationResults }) => {
  // Extract flags from validation results if not provided directly
  const flags = reviewFlags || [];
  
  // Categorize flags by severity
  const criticalFlags = flags.filter(flag => 
    flag.severity === 'CRITICAL' || flag.severity === 'HIGH'
  );
  const warningFlags = flags.filter(flag => 
    flag.severity === 'MEDIUM'
  );
  const infoFlags = flags.filter(flag => 
    flag.severity === 'LOW' || flag.severity === 'INFO'
  );

  // If validation results provided, extract critical issues
  const criticalIssues = validationResults?.critical_issues || [];
  const requiresReview = validationResults?.overall_status === 'FAIL' || 
                        validationResults?.overall_status === 'PASS_WITH_WARNINGS';

  // Calculate total flags
  const totalFlags = criticalFlags.length + warningFlags.length + infoFlags.length + criticalIssues.length;

  if (totalFlags === 0 && !requiresReview) {
    return (
      <Section className="review-flags-display review-flags-display--empty">
        <div className="review-flags-display__empty-state">
          <Checkmark className="review-flags-display__empty-icon" />
          <Heading className="review-flags-display__empty-heading">
            No Review Flags
          </Heading>
          <p className="review-flags-display__empty-text">
            All validation checks passed. The intake draft is ready for approval.
          </p>
        </div>
      </Section>
    );
  }

  return (
    <div className="review-flags-display">
      {/* Summary Header */}
      <Section className="review-flags-display__summary">
        <div className="review-flags-display__summary-content">
          <div className="review-flags-display__summary-icon">
            {requiresReview ? (
              <WarningAlt className="review-flags-display__icon review-flags-display__icon--warning" />
            ) : (
              <Information className="review-flags-display__icon review-flags-display__icon--info" />
            )}
          </div>
          <div className="review-flags-display__summary-text">
            <Heading className="review-flags-display__summary-heading">
              {requiresReview ? 'Review Required' : 'Review Recommended'}
            </Heading>
            <p className="review-flags-display__summary-description">
              {totalFlags} {totalFlags === 1 ? 'item' : 'items'} requiring attention
            </p>
          </div>
          <div className="review-flags-display__summary-badges">
            {criticalIssues.length > 0 && (
              <Tag type="red" size="lg">
                {criticalIssues.length} Critical
              </Tag>
            )}
            {criticalFlags.length > 0 && (
              <Tag type="red" size="lg">
                {criticalFlags.length} High
              </Tag>
            )}
            {warningFlags.length > 0 && (
              <Tag type="orange" size="lg">
                {warningFlags.length} Medium
              </Tag>
            )}
            {infoFlags.length > 0 && (
              <Tag type="blue" size="lg">
                {infoFlags.length} Low
              </Tag>
            )}
          </div>
        </div>
      </Section>

      {/* Critical Issues from Validation */}
      {criticalIssues.length > 0 && (
        <Section className="review-flags-display__section review-flags-display__section--critical">
          <Heading className="review-flags-display__section-heading">
            <Error className="review-flags-display__section-icon review-flags-display__section-icon--critical" />
            Critical Issues ({criticalIssues.length})
          </Heading>
          <div className="review-flags-display__flags-grid">
            {criticalIssues.map((issue, idx) => (
              <Tile key={idx} className="review-flags-display__flag-tile review-flags-display__flag-tile--critical">
                <div className="review-flags-display__flag-header">
                  <Tag type="red">{issue.severity}</Tag>
                  <Tag type="purple">{issue.category}</Tag>
                </div>
                <p className="review-flags-display__flag-issue">
                  {issue.issue}
                </p>
                <div className="review-flags-display__flag-recommendation">
                  <strong>Recommendation:</strong>
                  <p>{issue.recommendation}</p>
                </div>
              </Tile>
            ))}
          </div>
        </Section>
      )}

      {/* High Priority Flags */}
      {criticalFlags.length > 0 && (
        <Section className="review-flags-display__section review-flags-display__section--high">
          <Heading className="review-flags-display__section-heading">
            <WarningAlt className="review-flags-display__section-icon review-flags-display__section-icon--high" />
            High Priority ({criticalFlags.length})
          </Heading>
          <div className="review-flags-display__flags-grid">
            {criticalFlags.map((flag, idx) => (
              <Tile key={idx} className="review-flags-display__flag-tile review-flags-display__flag-tile--high">
                <div className="review-flags-display__flag-header">
                  <Tag type="red">{flag.severity}</Tag>
                  {flag.category && <Tag type="purple">{flag.category}</Tag>}
                </div>
                <p className="review-flags-display__flag-message">
                  {flag.message || flag.issue}
                </p>
                {flag.recommendation && (
                  <div className="review-flags-display__flag-recommendation">
                    <strong>Action:</strong>
                    <p>{flag.recommendation}</p>
                  </div>
                )}
              </Tile>
            ))}
          </div>
        </Section>
      )}

      {/* Medium Priority Flags */}
      {warningFlags.length > 0 && (
        <Section className="review-flags-display__section review-flags-display__section--medium">
          <Heading className="review-flags-display__section-heading">
            <WarningAlt className="review-flags-display__section-icon review-flags-display__section-icon--medium" />
            Medium Priority ({warningFlags.length})
          </Heading>
          <div className="review-flags-display__flags-grid">
            {warningFlags.map((flag, idx) => (
              <Tile key={idx} className="review-flags-display__flag-tile review-flags-display__flag-tile--medium">
                <div className="review-flags-display__flag-header">
                  <Tag type="orange">{flag.severity}</Tag>
                  {flag.category && <Tag type="purple">{flag.category}</Tag>}
                </div>
                <p className="review-flags-display__flag-message">
                  {flag.message || flag.issue}
                </p>
                {flag.recommendation && (
                  <div className="review-flags-display__flag-recommendation">
                    <strong>Action:</strong>
                    <p>{flag.recommendation}</p>
                  </div>
                )}
              </Tile>
            ))}
          </div>
        </Section>
      )}

      {/* Low Priority / Info Flags */}
      {infoFlags.length > 0 && (
        <Section className="review-flags-display__section review-flags-display__section--info">
          <Heading className="review-flags-display__section-heading">
            <Information className="review-flags-display__section-icon review-flags-display__section-icon--info" />
            Information ({infoFlags.length})
          </Heading>
          <div className="review-flags-display__flags-grid">
            {infoFlags.map((flag, idx) => (
              <Tile key={idx} className="review-flags-display__flag-tile review-flags-display__flag-tile--info">
                <div className="review-flags-display__flag-header">
                  <Tag type="blue">{flag.severity}</Tag>
                  {flag.category && <Tag type="purple">{flag.category}</Tag>}
                </div>
                <p className="review-flags-display__flag-message">
                  {flag.message || flag.issue}
                </p>
                {flag.recommendation && (
                  <div className="review-flags-display__flag-recommendation">
                    <strong>Note:</strong>
                    <p>{flag.recommendation}</p>
                  </div>
                )}
              </Tile>
            ))}
          </div>
        </Section>
      )}

      {/* Validation Summary */}
      {validationResults && (
        <Section className="review-flags-display__section review-flags-display__section--summary">
          <Heading className="review-flags-display__section-heading">
            Validation Summary
          </Heading>
          <div className="review-flags-display__validation-summary">
            <div className="review-flags-display__validation-metric">
              <span className="review-flags-display__validation-label">Overall Status:</span>
              <Tag 
                type={
                  validationResults.overall_status === 'PASS' ? 'green' :
                  validationResults.overall_status === 'PASS_WITH_WARNINGS' ? 'orange' :
                  'red'
                }
                size="lg"
              >
                {validationResults.overall_status}
              </Tag>
            </div>
            {validationResults.completeness && (
              <div className="review-flags-display__validation-metric">
                <span className="review-flags-display__validation-label">Completeness:</span>
                <Tag type={validationResults.completeness.status === 'PASS' ? 'green' : 'red'}>
                  {(validationResults.completeness.score * 100).toFixed(0)}%
                </Tag>
              </div>
            )}
            {validationResults.consistency && (
              <div className="review-flags-display__validation-metric">
                <span className="review-flags-display__validation-label">Consistency:</span>
                <Tag type={validationResults.consistency.status === 'PASS' ? 'green' : 'red'}>
                  {(validationResults.consistency.score * 100).toFixed(0)}%
                </Tag>
              </div>
            )}
            {validationResults.evidence_support && (
              <div className="review-flags-display__validation-metric">
                <span className="review-flags-display__validation-label">Evidence Support:</span>
                <Tag type={validationResults.evidence_support.status === 'PASS' ? 'green' : 'red'}>
                  {(validationResults.evidence_support.score * 100).toFixed(0)}%
                </Tag>
              </div>
            )}
          </div>
        </Section>
      )}
    </div>
  );
};

export default ReviewFlagsDisplay;

// Made with Bob
