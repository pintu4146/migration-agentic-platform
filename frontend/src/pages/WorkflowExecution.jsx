import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Button,
  Tile,
  Loading,
  InlineNotification,
  ProgressIndicator,
  ProgressStep,
  Accordion,
  AccordionItem,
  CodeSnippet,
} from '@carbon/react';
import { Play, Renew, CheckmarkFilled } from '@carbon/icons-react';
import {
  startWorkflow,
  executeWorkflow,
  getWorkflowState,
} from '../services/api';
import './WorkflowExecution.scss';

const WorkflowExecution = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    loadState();
  }, [projectId]);

  const loadState = async () => {
    try {
      setLoading(true);
      const response = await getWorkflowState(projectId);
      setState(response);
      setError(null);
    } catch (err) {
      if (err.response?.status === 404) {
        setState(null);
      } else {
        setError('Failed to load workflow state');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    try {
      setExecuting(true);
      setError(null);
      const response = await startWorkflow(projectId);
      setState(response);
      setSuccess('Workflow initialized successfully');
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
      const response = await executeWorkflow(projectId);
      setState(response);
      setSuccess('Workflow executed successfully');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to execute workflow');
    } finally {
      setExecuting(false);
    }
  };

  const getPhaseIndex = (phase) => {
    const phases = [
      'init',
      'context_retrieval',
      'extraction',
      'questionnaire',
      'intake_draft',
      'human_review',
      'migration_planning',
      'validation',
      'complete',
    ];
    return phases.indexOf(phase);
  };

  const currentPhaseIndex = state ? getPhaseIndex(state.phase) : 0;

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Workflow Execution</h1>
        <p className="page-description">
          Project: <strong>{projectId}</strong>
        </p>
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
              <Tile className="workflow-tile">
                <div className="workflow-header">
                  <div className="workflow-info">
                    <h3>Workflow Status</h3>
                    <div className="status-badge">
                      Phase: <strong>{state.phase}</strong>
                    </div>
                    <div className="status-badge">
                      Version: <strong>v{state.state_version}</strong>
                    </div>
                  </div>
                  <div className="workflow-actions">
                    <Button
                      kind="secondary"
                      renderIcon={Renew}
                      onClick={loadState}
                      size="sm"
                    >
                      Refresh
                    </Button>
                    <Button
                      kind="primary"
                      renderIcon={Play}
                      onClick={handleExecute}
                      disabled={executing || state.phase === 'complete'}
                      size="sm"
                    >
                      {executing ? 'Executing...' : 'Execute Next Step'}
                    </Button>
                  </div>
                </div>

                <ProgressIndicator currentIndex={currentPhaseIndex} spaceEqually>
                  <ProgressStep
                    label="Initialize"
                    description="Setup workflow"
                    complete={currentPhaseIndex > 0}
                  />
                  <ProgressStep
                    label="Context Retrieval"
                    description="Fetch documents"
                    complete={currentPhaseIndex > 1}
                  />
                  <ProgressStep
                    label="Extraction"
                    description="Extract facts"
                    complete={currentPhaseIndex > 2}
                  />
                  <ProgressStep
                    label="Questionnaire"
                    description="Generate questions"
                    complete={currentPhaseIndex > 3}
                  />
                  <ProgressStep
                    label="Intake Draft"
                    description="Create draft"
                    complete={currentPhaseIndex > 4}
                  />
                  <ProgressStep
                    label="Human Review"
                    description="Review required"
                    complete={currentPhaseIndex > 5}
                  />
                  <ProgressStep
                    label="Migration Plan"
                    description="Generate plan"
                    complete={currentPhaseIndex > 6}
                  />
                  <ProgressStep
                    label="Validation"
                    description="Validate output"
                    complete={currentPhaseIndex > 7}
                  />
                  <ProgressStep
                    label="Complete"
                    description="Workflow done"
                    complete={currentPhaseIndex >= 8}
                  />
                </ProgressIndicator>
              </Tile>

              <Accordion>
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
