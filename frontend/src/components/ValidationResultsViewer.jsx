import React from 'react';
import {
  Accordion,
  AccordionItem,
  Tag,
  ProgressBar,
  StructuredListWrapper,
  StructuredListHead,
  StructuredListRow,
  StructuredListCell,
  StructuredListBody,
  Section,
  Heading
} from '@carbon/react';
import { Checkmark, WarningAlt, Error, Information } from '@carbon/icons-react';
import './ValidationResultsViewer.scss';

/**
 * ValidationResultsViewer Component
 * 
 * Displays validation results from the ReviewValidationAgent:
 * - Overall status
 * - Completeness score and findings
 * - Consistency score and issues
 * - Evidence support score
 * - Clarity score
 * - Risk assessment score
 * - Critical issues
 * - Recommendations
 */
const ValidationResultsViewer = ({ validationResults }) => {
  if (!validationResults) {
    return (
      <Section className="validation-results-viewer validation-results-viewer--empty">
        <Heading className="validation-results-viewer__empty-heading">
          No validation results available
        </Heading>
        <p className="validation-results-viewer__empty-text">
          Validation results will be available after the intake draft is generated.
        </p>
      </Section>
    );
  }

  const {
    overall_status,
    completeness,
    consistency,
    evidence_support,
    clarity,
    risk_assessment,
    critical_issues,
    recommendations
  } = validationResults;

  // Helper function to get status icon
  const getStatusIcon = (status) => {
    switch (status?.toUpperCase()) {
      case 'PASS':
        return <Checkmark className="validation-results-viewer__status-icon validation-results-viewer__status-icon--pass" />;
      case 'PASS_WITH_WARNINGS':
        return <WarningAlt className="validation-results-viewer__status-icon validation-results-viewer__status-icon--warning" />;
      case 'FAIL':
        return <Error className="validation-results-viewer__status-icon validation-results-viewer__status-icon--fail" />;
      default:
        return <Information className="validation-results-viewer__status-icon validation-results-viewer__status-icon--info" />;
    }
  };

  // Helper function to get status tag type
  const getStatusTagType = (status) => {
    switch (status?.toUpperCase()) {
      case 'PASS':
        return 'green';
      case 'PASS_WITH_WARNINGS':
        return 'orange';
      case 'FAIL':
        return 'red';
      default:
        return 'gray';
    }
  };

  // Helper function to get severity tag type
  const getSeverityTagType = (severity) => {
    switch (severity?.toUpperCase()) {
      case 'CRITICAL':
        return 'red';
      case 'HIGH':
        return 'red';
      case 'MEDIUM':
        return 'orange';
      case 'LOW':
        return 'blue';
      default:
        return 'gray';
    }
  };

  return (
    <div className="validation-results-viewer">
      {/* Overall Status */}
      <Section className="validation-results-viewer__section validation-results-viewer__section--overall">
        <div className="validation-results-viewer__overall-status">
          {getStatusIcon(overall_status)}
          <Heading className="validation-results-viewer__overall-heading">
            Overall Status: {overall_status}
          </Heading>
          <Tag type={getStatusTagType(overall_status)} size="lg">
            {overall_status}
          </Tag>
        </div>
      </Section>

      {/* Validation Metrics */}
      <Section className="validation-results-viewer__section">
        <Heading className="validation-results-viewer__section-heading">
          Validation Metrics
        </Heading>
        <div className="validation-results-viewer__metrics">
          {/* Completeness */}
          {completeness && (
            <div className="validation-results-viewer__metric">
              <div className="validation-results-viewer__metric-header">
                <span className="validation-results-viewer__metric-label">Completeness</span>
                <Tag type={getStatusTagType(completeness.status)}>
                  {completeness.status}
                </Tag>
              </div>
              <ProgressBar
                label="Score"
                value={completeness.score * 100}
                max={100}
                className="validation-results-viewer__progress"
              />
              <span className="validation-results-viewer__metric-score">
                {(completeness.score * 100).toFixed(0)}%
              </span>
            </div>
          )}

          {/* Consistency */}
          {consistency && (
            <div className="validation-results-viewer__metric">
              <div className="validation-results-viewer__metric-header">
                <span className="validation-results-viewer__metric-label">Consistency</span>
                <Tag type={getStatusTagType(consistency.status)}>
                  {consistency.status}
                </Tag>
              </div>
              <ProgressBar
                label="Score"
                value={consistency.score * 100}
                max={100}
                className="validation-results-viewer__progress"
              />
              <span className="validation-results-viewer__metric-score">
                {(consistency.score * 100).toFixed(0)}%
              </span>
            </div>
          )}

          {/* Evidence Support */}
          {evidence_support && (
            <div className="validation-results-viewer__metric">
              <div className="validation-results-viewer__metric-header">
                <span className="validation-results-viewer__metric-label">Evidence Support</span>
                <Tag type={getStatusTagType(evidence_support.status)}>
                  {evidence_support.status}
                </Tag>
              </div>
              <ProgressBar
                label="Score"
                value={evidence_support.score * 100}
                max={100}
                className="validation-results-viewer__progress"
              />
              <span className="validation-results-viewer__metric-score">
                {(evidence_support.score * 100).toFixed(0)}%
              </span>
            </div>
          )}

          {/* Clarity */}
          {clarity && (
            <div className="validation-results-viewer__metric">
              <div className="validation-results-viewer__metric-header">
                <span className="validation-results-viewer__metric-label">Clarity</span>
                <Tag type={getStatusTagType(clarity.status)}>
                  {clarity.status}
                </Tag>
              </div>
              <ProgressBar
                label="Score"
                value={clarity.score * 100}
                max={100}
                className="validation-results-viewer__progress"
              />
              <span className="validation-results-viewer__metric-score">
                {(clarity.score * 100).toFixed(0)}%
              </span>
            </div>
          )}

          {/* Risk Assessment */}
          {risk_assessment && (
            <div className="validation-results-viewer__metric">
              <div className="validation-results-viewer__metric-header">
                <span className="validation-results-viewer__metric-label">Risk Assessment</span>
                <Tag type={getStatusTagType(risk_assessment.status)}>
                  {risk_assessment.status}
                </Tag>
              </div>
              <ProgressBar
                label="Score"
                value={risk_assessment.score * 100}
                max={100}
                className="validation-results-viewer__progress"
              />
              <span className="validation-results-viewer__metric-score">
                {(risk_assessment.score * 100).toFixed(0)}%
              </span>
            </div>
          )}
        </div>
      </Section>

      {/* Detailed Findings */}
      <Section className="validation-results-viewer__section">
        <Heading className="validation-results-viewer__section-heading">
          Detailed Findings
        </Heading>
        <Accordion>
          {/* Completeness Findings */}
          {completeness && completeness.findings && completeness.findings.length > 0 && (
            <AccordionItem title={`Completeness Issues (${completeness.findings.length})`}>
              <ul className="validation-results-viewer__findings-list">
                {completeness.findings.map((finding, idx) => (
                  <li key={idx} className="validation-results-viewer__finding-item">
                    <WarningAlt className="validation-results-viewer__finding-icon" />
                    {finding}
                  </li>
                ))}
              </ul>
              {completeness.missing_sections && completeness.missing_sections.length > 0 && (
                <div className="validation-results-viewer__missing-sections">
                  <strong>Missing Sections:</strong>
                  <div className="validation-results-viewer__tags">
                    {completeness.missing_sections.map((section, idx) => (
                      <Tag key={idx} type="red">
                        {section}
                      </Tag>
                    ))}
                  </div>
                </div>
              )}
            </AccordionItem>
          )}

          {/* Consistency Issues */}
          {consistency && (
            <AccordionItem 
              title={`Consistency Issues (${
                (consistency.contradictions?.length || 0) + 
                (consistency.alignment_issues?.length || 0)
              })`}
            >
              {consistency.contradictions && consistency.contradictions.length > 0 && (
                <div className="validation-results-viewer__subsection">
                  <strong>Contradictions:</strong>
                  <ul className="validation-results-viewer__findings-list">
                    {consistency.contradictions.map((contradiction, idx) => (
                      <li key={idx} className="validation-results-viewer__finding-item">
                        <Error className="validation-results-viewer__finding-icon validation-results-viewer__finding-icon--error" />
                        {contradiction}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {consistency.alignment_issues && consistency.alignment_issues.length > 0 && (
                <div className="validation-results-viewer__subsection">
                  <strong>Alignment Issues:</strong>
                  <ul className="validation-results-viewer__findings-list">
                    {consistency.alignment_issues.map((issue, idx) => (
                      <li key={idx} className="validation-results-viewer__finding-item">
                        <WarningAlt className="validation-results-viewer__finding-icon" />
                        {issue}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </AccordionItem>
          )}

          {/* Evidence Support Issues */}
          {evidence_support && (
            <AccordionItem 
              title={`Evidence Support Issues (${
                (evidence_support.unsupported_claims?.length || 0) + 
                (evidence_support.low_confidence_areas?.length || 0)
              })`}
            >
              {evidence_support.unsupported_claims && evidence_support.unsupported_claims.length > 0 && (
                <div className="validation-results-viewer__subsection">
                  <strong>Unsupported Claims:</strong>
                  <ul className="validation-results-viewer__findings-list">
                    {evidence_support.unsupported_claims.map((claim, idx) => (
                      <li key={idx} className="validation-results-viewer__finding-item">
                        <Error className="validation-results-viewer__finding-icon validation-results-viewer__finding-icon--error" />
                        {claim}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {evidence_support.low_confidence_areas && evidence_support.low_confidence_areas.length > 0 && (
                <div className="validation-results-viewer__subsection">
                  <strong>Low Confidence Areas:</strong>
                  <div className="validation-results-viewer__tags">
                    {evidence_support.low_confidence_areas.map((area, idx) => (
                      <Tag key={idx} type="orange">
                        {area}
                      </Tag>
                    ))}
                  </div>
                </div>
              )}
            </AccordionItem>
          )}

          {/* Clarity Issues */}
          {clarity && (
            <AccordionItem 
              title={`Clarity Issues (${
                (clarity.unclear_sections?.length || 0) + 
                (clarity.improvement_suggestions?.length || 0)
              })`}
            >
              {clarity.unclear_sections && clarity.unclear_sections.length > 0 && (
                <div className="validation-results-viewer__subsection">
                  <strong>Unclear Sections:</strong>
                  <ul className="validation-results-viewer__findings-list">
                    {clarity.unclear_sections.map((section, idx) => (
                      <li key={idx} className="validation-results-viewer__finding-item">
                        <WarningAlt className="validation-results-viewer__finding-icon" />
                        {section}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {clarity.improvement_suggestions && clarity.improvement_suggestions.length > 0 && (
                <div className="validation-results-viewer__subsection">
                  <strong>Improvement Suggestions:</strong>
                  <ul className="validation-results-viewer__findings-list">
                    {clarity.improvement_suggestions.map((suggestion, idx) => (
                      <li key={idx} className="validation-results-viewer__finding-item">
                        <Information className="validation-results-viewer__finding-icon validation-results-viewer__finding-icon--info" />
                        {suggestion}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </AccordionItem>
          )}
        </Accordion>
      </Section>

      {/* Critical Issues */}
      {critical_issues && critical_issues.length > 0 && (
        <Section className="validation-results-viewer__section validation-results-viewer__section--critical">
          <Heading className="validation-results-viewer__section-heading">
            Critical Issues ({critical_issues.length})
          </Heading>
          <StructuredListWrapper>
            <StructuredListHead>
              <StructuredListRow head>
                <StructuredListCell head>Issue</StructuredListCell>
                <StructuredListCell head>Severity</StructuredListCell>
                <StructuredListCell head>Category</StructuredListCell>
                <StructuredListCell head>Recommendation</StructuredListCell>
              </StructuredListRow>
            </StructuredListHead>
            <StructuredListBody>
              {critical_issues.map((issue, idx) => (
                <StructuredListRow key={idx}>
                  <StructuredListCell>
                    {issue.issue}
                  </StructuredListCell>
                  <StructuredListCell>
                    <Tag type={getSeverityTagType(issue.severity)}>
                      {issue.severity}
                    </Tag>
                  </StructuredListCell>
                  <StructuredListCell>
                    <Tag type="purple">{issue.category}</Tag>
                  </StructuredListCell>
                  <StructuredListCell>
                    {issue.recommendation}
                  </StructuredListCell>
                </StructuredListRow>
              ))}
            </StructuredListBody>
          </StructuredListWrapper>
        </Section>
      )}

      {/* Recommendations */}
      {recommendations && recommendations.length > 0 && (
        <Section className="validation-results-viewer__section">
          <Heading className="validation-results-viewer__section-heading">
            Recommendations ({recommendations.length})
          </Heading>
          <ul className="validation-results-viewer__recommendations-list">
            {recommendations.map((recommendation, idx) => (
              <li key={idx} className="validation-results-viewer__recommendation-item">
                <Checkmark className="validation-results-viewer__recommendation-icon" />
                {recommendation}
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  );
};

export default ValidationResultsViewer;

// Made with Bob
