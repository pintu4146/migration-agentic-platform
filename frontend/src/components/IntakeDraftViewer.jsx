import React from 'react';
import {
  Accordion,
  AccordionItem,
  Tag,
  StructuredListWrapper,
  StructuredListHead,
  StructuredListRow,
  StructuredListCell,
  StructuredListBody,
  Section,
  Heading
} from '@carbon/react';
import { Checkmark, WarningAlt, Information } from '@carbon/icons-react';
import './IntakeDraftViewer.scss';

/**
 * IntakeDraftViewer Component
 * 
 * Displays the generated intake draft with all sections:
 * - Executive Summary
 * - Current State (technical stack, architecture, deployment, scale)
 * - Dependencies (databases, external APIs, third-party services, internal systems)
 * - Constraints
 * - Assumptions
 * - Risks
 * - Open Questions
 * - Recommendations
 */
const IntakeDraftViewer = ({ intakeDraft }) => {
  if (!intakeDraft) {
    return (
      <Section className="intake-draft-viewer intake-draft-viewer--empty">
        <Heading className="intake-draft-viewer__empty-heading">
          No intake draft available
        </Heading>
        <p className="intake-draft-viewer__empty-text">
          The intake draft will be generated after fact extraction and questionnaire completion.
        </p>
      </Section>
    );
  }

  const {
    executive_summary,
    current_state,
    dependencies,
    constraints,
    assumptions,
    risks,
    open_questions,
    recommendations
  } = intakeDraft;

  return (
    <div className="intake-draft-viewer">
      {/* Executive Summary */}
      {executive_summary && (
        <Section className="intake-draft-viewer__section">
          <Heading className="intake-draft-viewer__section-heading">
            Executive Summary
          </Heading>
          <p className="intake-draft-viewer__summary-text">
            {executive_summary}
          </p>
        </Section>
      )}

      {/* Current State */}
      {current_state && (
        <Section className="intake-draft-viewer__section">
          <Heading className="intake-draft-viewer__section-heading">
            Current State
          </Heading>
          <Accordion>
            {current_state.technical_stack && (
              <AccordionItem title="Technical Stack">
                <p className="intake-draft-viewer__text">
                  {current_state.technical_stack}
                </p>
              </AccordionItem>
            )}
            {current_state.architecture && (
              <AccordionItem title="Architecture">
                <p className="intake-draft-viewer__text">
                  {current_state.architecture}
                </p>
              </AccordionItem>
            )}
            {current_state.deployment && (
              <AccordionItem title="Deployment">
                <p className="intake-draft-viewer__text">
                  {current_state.deployment}
                </p>
              </AccordionItem>
            )}
            {current_state.scale && (
              <AccordionItem title="Scale">
                <p className="intake-draft-viewer__text">
                  {current_state.scale}
                </p>
              </AccordionItem>
            )}
          </Accordion>
        </Section>
      )}

      {/* Dependencies */}
      {dependencies && (
        <Section className="intake-draft-viewer__section">
          <Heading className="intake-draft-viewer__section-heading">
            Dependencies
          </Heading>
          <StructuredListWrapper>
            <StructuredListHead>
              <StructuredListRow head>
                <StructuredListCell head>Category</StructuredListCell>
                <StructuredListCell head>Items</StructuredListCell>
              </StructuredListRow>
            </StructuredListHead>
            <StructuredListBody>
              {dependencies.databases && dependencies.databases.length > 0 && (
                <StructuredListRow>
                  <StructuredListCell>Databases</StructuredListCell>
                  <StructuredListCell>
                    {dependencies.databases.map((db, idx) => (
                      <Tag key={idx} type="blue" className="intake-draft-viewer__tag">
                        {db}
                      </Tag>
                    ))}
                  </StructuredListCell>
                </StructuredListRow>
              )}
              {dependencies.external_apis && dependencies.external_apis.length > 0 && (
                <StructuredListRow>
                  <StructuredListCell>External APIs</StructuredListCell>
                  <StructuredListCell>
                    {dependencies.external_apis.map((api, idx) => (
                      <Tag key={idx} type="purple" className="intake-draft-viewer__tag">
                        {api}
                      </Tag>
                    ))}
                  </StructuredListCell>
                </StructuredListRow>
              )}
              {dependencies.third_party_services && dependencies.third_party_services.length > 0 && (
                <StructuredListRow>
                  <StructuredListCell>Third-party Services</StructuredListCell>
                  <StructuredListCell>
                    {dependencies.third_party_services.map((service, idx) => (
                      <Tag key={idx} type="teal" className="intake-draft-viewer__tag">
                        {service}
                      </Tag>
                    ))}
                  </StructuredListCell>
                </StructuredListRow>
              )}
              {dependencies.internal_systems && dependencies.internal_systems.length > 0 && (
                <StructuredListRow>
                  <StructuredListCell>Internal Systems</StructuredListCell>
                  <StructuredListCell>
                    {dependencies.internal_systems.map((system, idx) => (
                      <Tag key={idx} type="cyan" className="intake-draft-viewer__tag">
                        {system}
                      </Tag>
                    ))}
                  </StructuredListCell>
                </StructuredListRow>
              )}
            </StructuredListBody>
          </StructuredListWrapper>
        </Section>
      )}

      {/* Constraints */}
      {constraints && constraints.length > 0 && (
        <Section className="intake-draft-viewer__section">
          <Heading className="intake-draft-viewer__section-heading">
            Constraints
          </Heading>
          <ul className="intake-draft-viewer__list">
            {constraints.map((constraint, idx) => (
              <li key={idx} className="intake-draft-viewer__list-item">
                <Information className="intake-draft-viewer__icon intake-draft-viewer__icon--info" />
                <div>
                  <strong>{constraint.type || 'Constraint'}:</strong> {constraint.description}
                  {constraint.impact && (
                    <div className="intake-draft-viewer__constraint-impact">
                      <em>Impact: {constraint.impact}</em>
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {/* Assumptions */}
      {assumptions && assumptions.length > 0 && (
        <Section className="intake-draft-viewer__section">
          <Heading className="intake-draft-viewer__section-heading">
            Assumptions
          </Heading>
          <StructuredListWrapper>
            <StructuredListHead>
              <StructuredListRow head>
                <StructuredListCell head>Assumption</StructuredListCell>
                <StructuredListCell head>Confidence</StructuredListCell>
                <StructuredListCell head>Validation</StructuredListCell>
              </StructuredListRow>
            </StructuredListHead>
            <StructuredListBody>
              {assumptions.map((assumption, idx) => (
                <StructuredListRow key={idx}>
                  <StructuredListCell>
                    {assumption.assumption}
                  </StructuredListCell>
                  <StructuredListCell>
                    <Tag
                      type={
                        parseFloat(assumption.confidence) >= 0.8
                          ? 'green'
                          : parseFloat(assumption.confidence) >= 0.5
                          ? 'blue'
                          : 'red'
                      }
                    >
                      {(parseFloat(assumption.confidence) * 100).toFixed(0)}%
                    </Tag>
                  </StructuredListCell>
                  <StructuredListCell>
                    {assumption.needs_validation ? (
                      <Tag type="red">Needs Validation</Tag>
                    ) : (
                      <Tag type="green">
                        <Checkmark /> Validated
                      </Tag>
                    )}
                  </StructuredListCell>
                </StructuredListRow>
              ))}
            </StructuredListBody>
          </StructuredListWrapper>
        </Section>
      )}

      {/* Risks */}
      {risks && risks.length > 0 && (
        <Section className="intake-draft-viewer__section">
          <Heading className="intake-draft-viewer__section-heading">
            Risks
          </Heading>
          <StructuredListWrapper>
            <StructuredListHead>
              <StructuredListRow head>
                <StructuredListCell head>Risk</StructuredListCell>
                <StructuredListCell head>Severity</StructuredListCell>
                <StructuredListCell head>Mitigation</StructuredListCell>
              </StructuredListRow>
            </StructuredListHead>
            <StructuredListBody>
              {risks.map((risk, idx) => (
                <StructuredListRow key={idx}>
                  <StructuredListCell>
                    {risk.risk}
                  </StructuredListCell>
                  <StructuredListCell>
                    <Tag
                      type={
                        risk.severity === 'High' || risk.severity === 'CRITICAL'
                          ? 'red'
                          : risk.severity === 'Medium'
                          ? 'orange'
                          : 'blue'
                      }
                    >
                      <WarningAlt /> {risk.severity}
                    </Tag>
                  </StructuredListCell>
                  <StructuredListCell>
                    {risk.mitigation}
                  </StructuredListCell>
                </StructuredListRow>
              ))}
            </StructuredListBody>
          </StructuredListWrapper>
        </Section>
      )}

      {/* Open Questions */}
      {open_questions && open_questions.length > 0 && (
        <Section className="intake-draft-viewer__section">
          <Heading className="intake-draft-viewer__section-heading">
            Open Questions
          </Heading>
          <StructuredListWrapper>
            <StructuredListHead>
              <StructuredListRow head>
                <StructuredListCell head>Question</StructuredListCell>
                <StructuredListCell head>Priority</StructuredListCell>
                <StructuredListCell head>Category</StructuredListCell>
              </StructuredListRow>
            </StructuredListHead>
            <StructuredListBody>
              {open_questions.map((question, idx) => (
                <StructuredListRow key={idx}>
                  <StructuredListCell>
                    {question.question}
                  </StructuredListCell>
                  <StructuredListCell>
                    <Tag
                      type={
                        question.priority === 'High' || question.priority === 'HIGH'
                          ? 'red'
                          : question.priority === 'Medium' || question.priority === 'MEDIUM'
                          ? 'blue'
                          : 'gray'
                      }
                    >
                      {question.priority}
                    </Tag>
                  </StructuredListCell>
                  <StructuredListCell>
                    <Tag type="purple">{question.category}</Tag>
                  </StructuredListCell>
                </StructuredListRow>
              ))}
            </StructuredListBody>
          </StructuredListWrapper>
        </Section>
      )}

      {/* Recommendations */}
      {recommendations && recommendations.length > 0 && (
        <Section className="intake-draft-viewer__section">
          <Heading className="intake-draft-viewer__section-heading">
            Recommendations
          </Heading>
          <StructuredListWrapper>
            <StructuredListHead>
              <StructuredListRow head>
                <StructuredListCell head>Recommendation</StructuredListCell>
                <StructuredListCell head>Rationale</StructuredListCell>
                <StructuredListCell head>Priority</StructuredListCell>
              </StructuredListRow>
            </StructuredListHead>
            <StructuredListBody>
              {recommendations.map((rec, idx) => (
                <StructuredListRow key={idx}>
                  <StructuredListCell>
                    {rec.recommendation}
                  </StructuredListCell>
                  <StructuredListCell>
                    {rec.rationale}
                  </StructuredListCell>
                  <StructuredListCell>
                    <Tag
                      type={
                        rec.priority === 'High' || rec.priority === 'HIGH'
                          ? 'red'
                          : rec.priority === 'Medium' || rec.priority === 'MEDIUM'
                          ? 'blue'
                          : 'gray'
                      }
                    >
                      {rec.priority}
                    </Tag>
                  </StructuredListCell>
                </StructuredListRow>
              ))}
            </StructuredListBody>
          </StructuredListWrapper>
        </Section>
      )}
    </div>
  );
};

export default IntakeDraftViewer;

// Made with Bob
