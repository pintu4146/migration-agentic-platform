import { useState, useEffect } from 'react';
import { Dropdown, Button } from '@carbon/react';
import { Add } from '@carbon/icons-react';
import { listProjects } from '../services/api';
import ProjectCreationModal from './ProjectCreationModal';
import './ProjectSelector.scss';

const ProjectSelector = ({ value, onChange, label = 'Select Project', disabled = false }) => {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      setLoading(true);
      const response = await listProjects();
      setProjects(response.projects || []);
      setError(null);
    } catch (err) {
      console.error('Failed to load projects:', err);
      setError('Failed to load projects');
      setProjects([]);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = ({ selectedItem }) => {
    if (selectedItem && onChange) {
      onChange(selectedItem.id);
    }
  };

  const handleProjectCreated = (newProject) => {
    // Reload projects list
    loadProjects();
    
    // Auto-select the newly created project
    if (onChange && newProject.project_id) {
      onChange(newProject.project_id);
    }
  };

  const selectedProject = projects.find(p => p.id === value);

  return (
    <div className="project-selector">
      <div className="project-selector-header">
        <Button
          kind="primary"
          size="sm"
          renderIcon={Add}
          onClick={() => setModalOpen(true)}
          disabled={disabled}
        >
          Create New Project
        </Button>
      </div>
      
      <Dropdown
        id="project-selector-dropdown"
        titleText={label}
        label={loading ? 'Loading projects...' : projects.length === 0 ? 'No projects yet - create one above' : 'Choose a project'}
        items={projects}
        itemToString={(item) => item ? `${item.name} (${item.document_count} docs)` : ''}
        selectedItem={selectedProject}
        onChange={handleChange}
        disabled={disabled || loading}
        invalid={!!error}
        invalidText={error}
      />

      <ProjectCreationModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={handleProjectCreated}
      />
    </div>
  );
};

export default ProjectSelector;

// Made with Bob