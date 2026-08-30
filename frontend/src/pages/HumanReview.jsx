import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import {
  Button,
  Tabs,
  TabList,
  Tab,
  TabPanels,
  TabPanel,
  Modal,
  TextArea,
  InlineNotification,
  Loading
} from '@carbon/react';
import { Checkmark, Close, Chat } from '@carbon/icons-react';
import IntakeDraftViewer from '../components/IntakeDraftViewer';
import ValidationResultsViewer from '../components/ValidationResultsViewer';
import ReviewFlagsDisplay from '../components/ReviewFlagsDisplay';
import ChatDrawer from '../components/ChatDrawer';
import AssistancePanel from '../components/AssistancePanel';
import { resumeWorkflow, getWorkflowState } from '../services/api';
import './HumanReview.scss';

/**
 * HumanReview Page
 *
 * Displays the intake draft, validation results, and review flags
 * for human review and approval.
 *
 * Features:
 * - Tabbed interface for intake draft, validation, and flags
 * - Approve/Reject workflow actions
 * - Comments/feedback input
 * - Real-time state updates
 */
const HumanReview = () => {
  const { projectId } = useParams();
  const [workflowState, setWorkflowState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedTab, setSelectedTab] = useState(0);
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [comments, setComments] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);

  // Load workflow state
  useEffect(() => {
    const loadState = async () => {
      if (!projectId) {
        setError('No project selected');
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        const state = await getWorkflowState(projectId);
        setWorkflowState(state);
      } catch (err) {
        console.error('Failed to load workflow state:', err);
        setError(err.message || 'Failed to load workflow state');
      } finally {
        setLoading(false);
      }
    };

    loadState();
  }, [projectId]);

  // Handle approve
  const handleApprove = async () => {
    try {
      setSubmitting(true);
      setError(null);

      await resumeWorkflow(projectId, {
        human_reviewed: true,
        review_approved: true,
        review_comments: comments || 'Approved',
        reviewed_at: new Date().toISOString()
      });

      setSubmitSuccess(true);
      setShowApproveModal(false);
      
      // Reload state after approval
      setTimeout(async () => {
        const state = await getWorkflowState(projectId);
        setWorkflowState(state);
      }, 1000);
    } catch (err) {
      console.error('Failed to approve:', err);
      setError(err.message || 'Failed to approve workflow');
    } finally {
      setSubmitting(false);
    }
  };

  // Handle reject
  const handleReject = async () => {
    if (!comments.trim()) {
      setError('Please provide rejection reason');
      return;
    }

    try {
      setSubmitting(true);
      setError(null);

      await resumeWorkflow(projectId, {
        human_reviewed: true,
        review_approved: false,
        review_comments: comments,
        reviewed_at: new Date().toISOString()
      });

      setSubmitSuccess(true);
      setShowRejectModal(false);
      
      // Reload state after rejection
      setTimeout(async () => {
        const state = await getWorkflowState(projectId);
        setWorkflowState(state);
      }, 1000);
    } catch (err) {
      console.error('Failed to reject:', err);
      setError(err.message || 'Failed to reject workflow');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="human-review human-review--loading">
        <Loading description="Loading review data..." withOverlay={false} />
      </div>
    );
  }

  if (error && !workflowState) {
    return (
      <div className="human-review human-review--error">
        <InlineNotification
          kind="error"
          title="Error"
          subtitle={error}
          lowContrast
        />
      </div>
    );
  }

  const intakeDraft = workflowState?.intake_draft;
  const validationResults = workflowState?.validation_results;
  const reviewFlags = workflowState?.review_flags || [];
  const alreadyReviewed = workflowState?.human_reviewed;

  return (
    <div className="human-review">
      {/* Header */}
      <div className="human-review__header">
        <div className="human-review__header-content">
          <div className="human-review__header-text">
            <h2 className="human-review__title">
              Human Review
            </h2>
            <p className="human-review__subtitle">
              Review the intake draft and validation results before proceeding to migration planning
            </p>
          </div>
          {!alreadyReviewed && (
            <div className="human-review__header-actions">
              <Button
                kind="ghost"
                renderIcon={Chat}
                onClick={() => setIsChatOpen(true)}
              >
                Ask Assistant
              </Button>
              <Button
                kind="secondary"
                renderIcon={Close}
                onClick={() => setShowRejectModal(true)}
              >
                Reject
              </Button>
              <Button
                kind="primary"
                renderIcon={Checkmark}
                onClick={() => setShowApproveModal(true)}
              >
                Approve
              </Button>
            </div>
          )}
          {alreadyReviewed && (
            <div className="human-review__reviewed-badge">
              <Checkmark className="human-review__reviewed-icon" />
              <span>Already Reviewed</span>
            </div>
          )}
        </div>
      </div>

      {/* Success Notification */}
      {submitSuccess && (
        <InlineNotification
          kind="success"
          title="Success"
          subtitle="Review submitted successfully. Workflow will continue to migration planning."
          lowContrast
          onCloseButtonClick={() => setSubmitSuccess(false)}
        />
      )}

      {/* Error Notification */}
      {error && (
        <InlineNotification
          kind="error"
          title="Error"
          subtitle={error}
          lowContrast
          onCloseButtonClick={() => setError(null)}
        />
      )}

      {/* Tabbed Content */}
      <Tabs selectedIndex={selectedTab} onChange={({ selectedIndex }) => setSelectedTab(selectedIndex)}>
        <TabList aria-label="Review tabs" contained>
          <Tab>Review Flags</Tab>
          <Tab>Intake Draft</Tab>
          <Tab>Validation Results</Tab>
          <Tab>Advanced Assistant</Tab>
        </TabList>
        <TabPanels>
          {/* Review Flags Tab */}
          <TabPanel>
            <ReviewFlagsDisplay
              reviewFlags={reviewFlags}
              validationResults={validationResults}
            />
          </TabPanel>

          {/* Intake Draft Tab */}
          <TabPanel>
            <IntakeDraftViewer intakeDraft={intakeDraft} />
          </TabPanel>

          {/* Validation Results Tab */}
          <TabPanel>
            <ValidationResultsViewer validationResults={validationResults} />
          </TabPanel>

          {/* Advanced Assistant Tab */}
          <TabPanel>
            <AssistancePanel projectId={projectId} />
          </TabPanel>
        </TabPanels>
      </Tabs>

      {/* Approve Modal */}
      <Modal
        open={showApproveModal}
        onRequestClose={() => setShowApproveModal(false)}
        modalHeading="Approve Intake Draft"
        primaryButtonText="Approve"
        secondaryButtonText="Cancel"
        onRequestSubmit={handleApprove}
        primaryButtonDisabled={submitting}
      >
        <p className="human-review__modal-text">
          Are you sure you want to approve this intake draft? The workflow will proceed to migration planning.
        </p>
        <TextArea
          id="approve-comments"
          labelText="Comments (optional)"
          placeholder="Add any comments or notes..."
          value={comments}
          onChange={(e) => setComments(e.target.value)}
          rows={4}
        />
      </Modal>

      {/* Reject Modal */}
      <Modal
        open={showRejectModal}
        onRequestClose={() => setShowRejectModal(false)}
        modalHeading="Reject Intake Draft"
        primaryButtonText="Reject"
        secondaryButtonText="Cancel"
        onRequestSubmit={handleReject}
        primaryButtonDisabled={submitting || !comments.trim()}
        danger
      >
        <p className="human-review__modal-text">
          Please provide a reason for rejecting this intake draft. The workflow will be paused for revisions.
        </p>
        <TextArea
          id="reject-comments"
          labelText="Rejection Reason (required)"
          placeholder="Explain what needs to be revised..."
          value={comments}
          onChange={(e) => setComments(e.target.value)}
          rows={4}
          invalid={!comments.trim()}
          invalidText="Rejection reason is required"
        />
      </Modal>

      {/* Chat Drawer — slide-in assistant panel */}
      <ChatDrawer
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        projectId={projectId}
      />

      {/* Floating chat button — always visible bottom-right */}
      <button
        className="chat-fab"
        onClick={() => setIsChatOpen(true)}
        aria-label="Open assistant chat"
        title="Ask the Assistant"
      >
        <Chat />
      </button>
    </div>
  );
};

export default HumanReview;

// Made with Bob
