import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Button,
  Tile,
  Loading,
  InlineNotification,
  Accordion,
  AccordionItem,
  CodeSnippet,
  Grid,
  Column,
} from '@carbon/react';
import { Play, CheckmarkFilled } from '@carbon/icons-react';
import {
  startWorkflow,
  executeWorkflow,
} from '../services/api';
import ProjectSelector from '../components/ProjectSelector';
import useWorkflowSSE from '../hooks/useWorkflowSSE';
import WorkflowProgressStepper from '../components/WorkflowProgressStepper';
import CurrentPhasePanel from '../components/CurrentPhasePanel';
import { getCompletedPhases, getProgressPercentage } from '../utils/workflowHelpers';
import './WorkflowExecution.scss';

const WorkflowExecution = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Use SSE for real-time updates
  const { state, loading, error: sseError, isConnected, phaseInfo, phaseTransition, refetch } = useWorkflowSSE(projectId);

  // Merge SSE error with local error
  useEffect(() => {
    if (sseError) {
      setError(sseError);
    }
  }, [sseError]);

  const handleStart = async () => {
    try {
      setExecuting(true);
      setError(null);
      await startWorkflow(projectId);
      setSuccess('Workflow initialized successfully');
      // SSE will automatically receive the update
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start workflow');
    } finally {
      setExecuting(false);
    }
  };

  const handleExecute = async () => {
    try {
      setExecuting(true);
      setError(null);
      await executeWorkflow(projectId);
      setSuccess('Workflow step executed successfully');
      // SSE will automatically receive the update
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to execute workflow');
    } finally {
      setExecuting(false);
    }
  };

  const handleProjectChange = (newProjectId) => {
    navigate(`/workflow/${newProjectId}`);
  };

  // Extract phase data
  const completedPhases = state ? getCompletedPhases(state) : [];
  const progressPercentage = state ? getProgressPercentage(state) : 0;

  // Determine current phase status
  const getPhaseStatus = () => {
    if (!state) return 'in_progress';
    if (state.phase === 'complete') return 'completed';
    if (state.phase === 'human_review') return 'paused';
    if (state.error) return 'error';
    return 'in_progress';
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Workflow Execution</h1>
        <p className="page-description">
          Project: <strong>{projectId}</strong>
        </p>
      </div>

      <div style={{ marginBottom: '2rem', maxWidth: '400px' }}>
        <ProjectSelector
          value={projectId}
          onChange={handleProjectChange}
          label="Switch Project"
        />
      </div>

      {error && (
        <InlineNotification
          kind="error"
          title="Error"
          subtitle={error}
          onCloseButtonClick={() => setError(null)}
          style={{ marginBottom: '2rem' }}
        />
      )}

      {success && (
        <InlineNotification
          kind="success"
          title="Success"
          subtitle={success}
          onCloseButtonClick={() => setSuccess(null)}
          style={{ marginBottom: '2rem' }}
        />
      )}

      {loading ? (
        <Loading description="Loading workflow state..." withOverlay={false} />
      ) : (
        <>
          {!state ? (
            <Tile className="workflow-tile">
              <div className="empty-state">
                <h3>No workflow found for this project</h3>
                <p>Start a new workflow to begin the migration analysis process.</p>
                <Button
                  kind="primary"
                  renderIcon={Play}
                  onClick={handleStart}
                  disabled={executing}
                >
                  {executing ? 'Starting...' : 'Start Workflow'}
                </Button>
              </div>
            </Tile>
          ) : (
            <>
              {/* Current Phase Panel */}
              <CurrentPhasePanel
                phase={state.phase}
                status={getPhaseStatus()}
              />

              {/* Action Buttons */}
              <div className="workflow-actions-bar">
                <div className="workflow-meta">
                  <span className="meta-item">
                    Version: <strong>v{state.state_version}</strong>
                  </span>
                  <span className="meta-item">
                    Progress: <strong>{progressPercentage}%</strong>
                  </span>
                  <span className="meta-item">
                    Updated: <strong>{new Date(state.updated_at).toLocaleTimeString()}</strong>
                  </span>
                  {isConnected ? (
                    <span className="meta-item sse-indicator connected">
                      ⚡ Live Updates
                    </span>
                  ) : (
                    <span className="meta-item sse-indicator disconnected">
                      ⚠️ Reconnecting...
                    </span>
                  )}
                </div>
                <div className="action-buttons">
                  <Button
                    kind="primary"
                    renderIcon={Play}
                    onClick={handleExecute}
                    disabled={executing || state.phase === 'complete' || state.phase === 'human_review'}
                    size="md"
                  >
                    {executing ? 'Executing...' : 'Execute Next Step'}
                  </Button>
                </div>
              </div>

              {/* Progress Stepper */}
              <WorkflowProgressStepper
                currentPhase={state.phase}
                completedPhases={completedPhases}
              />

              {/* Phase Transition Notification */}
              {phaseTransition && (
                <InlineNotification
                  kind="info"
                  title="Phase Transition"
                  subtitle={`Workflow progressed from ${phaseTransition.from_phase} to ${phaseTransition.to_phase}`}
                  lowContrast
                  hideCloseButton
                  style={{ marginTop: '1rem', marginBottom: '1rem' }}
                />
              )}

              {/* Real-Time Phase Progress */}
              {phaseInfo && phaseInfo.details && (
                <Tile className="phase-progress-tile" style={{ marginTop: '1rem', marginBottom: '1rem' }}>
                  <h4>Current Phase: {phaseInfo.current_phase}</h4>
                  <div className="phase-details">
                    {phaseInfo.details.documents_retrieved !== undefined && (
                      <div className="detail-item">
                        <span className="detail-label">Documents Retrieved:</span>
                        <span className="detail-value">{phaseInfo.details.documents_retrieved}</span>
                      </div>
                    )}
                    {phaseInfo.details.facts_extracted !== undefined && (
                      <div className="detail-item">
                        <span className="detail-label">Facts Extracted:</span>
                        <span className="detail-value">{phaseInfo.details.facts_extracted}</span>
                      </div>
                    )}
                    {phaseInfo.details.categories && (
                      <div className="detail-item">
                        <span className="detail-label">Categories:</span>
                        <span className="detail-value">{phaseInfo.details.categories.join(', ')}</span>
                      </div>
                    )}
                    {phaseInfo.details.questions_generated !== undefined && (
                      <div className="detail-item">
                        <span className="detail-label">Questions Generated:</span>
                        <span className="detail-value">{phaseInfo.details.questions_generated}</span>
                      </div>
                    )}
                    {phaseInfo.details.high_priority_questions !== undefined && (
                      <div className="detail-item">
                        <span className="detail-label">High Priority:</span>
                        <span className="detail-value">{phaseInfo.details.high_priority_questions}</span>
                      </div>
                    )}
                    {phaseInfo.details.draft_created !== undefined && (
                      <div className="detail-item">
                        <span className="detail-label">Draft Status:</span>
                        <span className="detail-value">{phaseInfo.details.draft_created ? '✓ Created' : 'Pending'}</span>
                      </div>
                    )}
                    {phaseInfo.details.status && (
                      <div className="detail-item">
                        <span className="detail-label">Status:</span>
                        <span className="detail-value status-badge">{phaseInfo.details.status}</span>
                      </div>
                    )}
                  </div>
                </Tile>
              )}

              {/* Simple Status Summary */}
              <Grid className="phase-status-grid">
                <Column lg={5} md={4} sm={4}>
                  <Tile className="phase-status-card">
                    <h4>Context Pack</h4>
                    <div className="metric-large">
                      {state.context_pack ? '✓' : '—'}
                    </div>
                    <div className="metric-label">
                      {state.context_pack ? 'Retrieved' : 'Pending'}
                    </div>
                  </Tile>
                </Column>
                <Column lg={5} md={4} sm={4}>
                  <Tile className="phase-status-card">
                    <h4>Extracted Facts</h4>
                    <div className="metric-large">
                      {state.extracted_facts ? '✓' : '—'}
                    </div>
                    <div className="metric-label">
                      {state.extracted_facts ? 'Completed' : 'Pending'}
                    </div>
                  </Tile>
                </Column>
                <Column lg={6} md={4} sm={4}>
                  <Tile className="phase-status-card">
                    <h4>Questions</h4>
                    <div className="metric-large">
                      {state.missing_questions?.length || 0}
                    </div>
                    <div className="metric-label">
                      Gap Questions
                    </div>
                  </Tile>
                </Column>
              </Grid>

              {/* Detailed State Accordion */}
              <Accordion style={{ marginTop: '2rem' }}>
                <AccordionItem title="Workflow State Details">
                  <CodeSnippet type="multi" feedback="Copied to clipboard">
                    {JSON.stringify(state, null, 2)}
                  </CodeSnippet>
                </AccordionItem>

                {state.context_pack && (
                  <AccordionItem title="Context Pack">
                    <CodeSnippet type="multi" feedback="Copied to clipboard">
                      {JSON.stringify(state.context_pack, null, 2)}
                    </CodeSnippet>
                  </AccordionItem>
                )}

                {state.extracted_facts && (
                  <AccordionItem title="Extracted Facts">
                    <CodeSnippet type="multi" feedback="Copied to clipboard">
                      {JSON.stringify(state.extracted_facts, null, 2)}
                    </CodeSnippet>
                  </AccordionItem>
                )}

                {state.missing_questions && state.missing_questions.length > 0 && (
                  <AccordionItem title="Questionnaire Gaps">
                    <div className="questions-list">
                      {state.missing_questions.map((q, index) => (
                        <div key={index} className="question-item">
                          <strong>Q{index + 1}:</strong> {q.question}
                          <div className="question-meta">
                            Priority: {q.priority} | Category: {q.category}
                          </div>
                        </div>
                      ))}
                    </div>
                  </AccordionItem>
                )}
              </Accordion>

              {state.phase === 'complete' && (
                <Tile className="completion-tile">
                  <CheckmarkFilled size={32} className="completion-icon" />
                  <h3>Workflow Complete!</h3>
                  <p>The migration analysis workflow has been completed successfully.</p>
                  <Button
                    kind="primary"
                    onClick={() => navigate(`/facts/${projectId}`)}
                  >
                    View Extracted Facts
                  </Button>
                </Tile>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
};

export default WorkflowExecution;

// Made with Bob
