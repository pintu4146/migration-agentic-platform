import { Modal, Button } from '@carbon/react';
import { Restart, Play } from '@carbon/icons-react';
import PropTypes from 'prop-types';
import './WorkflowExistsModal.scss';

const WorkflowExistsModal = ({ open, onClose, onContinue, onRestart, existingPhase, loading }) => {
  return (
    <Modal
      open={open}
      onRequestClose={onClose}
      modalHeading="Workflow Already Exists"
      passiveModal={false}
      size="sm"
      preventCloseOnClickOutside={loading}
    >
      <div className="workflow-exists-modal-content">
        <p className="modal-description">
          A workflow already exists for this project at phase: <strong>{existingPhase}</strong>
        </p>
        <p className="modal-question">
          Would you like to continue from the current phase or restart the workflow from the beginning?
        </p>
        
        <div className="modal-actions">
          <Button
            kind="secondary"
            renderIcon={Play}
            onClick={onContinue}
            disabled={loading}
            className="continue-button"
          >
            Continue Workflow
          </Button>
          <Button
            kind="danger"
            renderIcon={Restart}
            onClick={onRestart}
            disabled={loading}
            className="restart-button"
          >
            {loading ? 'Restarting...' : 'Restart Workflow'}
          </Button>
        </div>
        
        <div className="modal-info">
          <p className="info-text">
            <strong>Continue:</strong> Resume from the current phase without losing progress.
          </p>
          <p className="info-text">
            <strong>Restart:</strong> Delete existing state and start fresh from the beginning.
          </p>
        </div>
      </div>
    </Modal>
  );
};

WorkflowExistsModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onContinue: PropTypes.func.isRequired,
  onRestart: PropTypes.func.isRequired,
  existingPhase: PropTypes.string,
  loading: PropTypes.bool,
};

WorkflowExistsModal.defaultProps = {
  existingPhase: 'unknown',
  loading: false,
};

export default WorkflowExistsModal;

// Made with Bob