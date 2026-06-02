import { useState } from 'react';
import {
  Modal,
  TextInput,
  TextArea,
  InlineNotification,
} from '@carbon/react';
import { createProject } from '../services/api';
import './ProjectCreationModal.scss';

const ProjectCreationModal = ({ open, onClose, onSuccess }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [nameError, setNameError] = useState('');

  const validateName = (value) => {
    if (!value || value.trim().length < 3) {
      setNameError('Project name must be at least 3 characters');
      return false;
    }
    if (value.length > 50) {
      setNameError('Project name must be less than 50 characters');
      return false;
    }
    setNameError('');
    return true;
  };

  const handleNameChange = (e) => {
    const value = e.target.value;
    setName(value);
    validateName(value);
  };

  const handleSubmit = async () => {
    // Validate
    if (!validateName(name)) {
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // Call API to create project
      const result = await createProject(name, description || null);

      // Success - notify parent and close
      if (onSuccess) {
        onSuccess(result);
      }

      // Reset form
      setName('');
      setDescription('');
      setNameError('');
      
      onClose();
    } catch (err) {
      console.error('Failed to create project:', err);
      
      // Handle specific error cases
      if (err.response?.status === 409) {
        setError('A project with this name already exists');
      } else if (err.response?.status === 400) {
        setError(err.response.data?.detail || 'Invalid project name');
      } else {
        setError('Failed to create project. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      setName('');
      setDescription('');
      setError(null);
      setNameError('');
      onClose();
    }
  };

  return (
    <Modal
      open={open}
      onRequestClose={handleClose}
      onRequestSubmit={handleSubmit}
      modalHeading="Create New Project"
      primaryButtonText="Create Project"
      secondaryButtonText="Cancel"
      primaryButtonDisabled={loading || !name || !!nameError}
      preventCloseOnClickOutside={loading}
      size="sm"
    >
      <div className="project-creation-form">
        {error && (
          <InlineNotification
            kind="error"
            title="Error"
            subtitle={error}
            onCloseButtonClick={() => setError(null)}
            lowContrast
            style={{ marginBottom: '1rem' }}
          />
        )}

        <TextInput
          id="project-name"
          labelText="Project Name"
          placeholder="e.g., Legacy App Migration"
          value={name}
          onChange={handleNameChange}
          invalid={!!nameError}
          invalidText={nameError}
          disabled={loading}
          required
          maxLength={50}
        />

        <TextArea
          id="project-description"
          labelText="Description (Optional)"
          placeholder="Brief description of the migration project..."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={loading}
          rows={4}
          maxLength={500}
          style={{ marginTop: '1rem' }}
        />

        <div className="character-count" style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: '#6f6f6f' }}>
          {description.length}/500 characters
        </div>
      </div>
    </Modal>
  );
};

export default ProjectCreationModal;

// Made with Bob