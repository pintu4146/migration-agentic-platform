import { useState, useEffect } from 'react';
import { Dropdown } from '@carbon/react';
import { listProjects } from '../services/api';
import './ProjectSelector.scss';

const ProjectSelector = ({ value, onChange, label = 'Select Project', disabled = false }) => {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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

  const selectedProject = projects.find(p => p.id === value);

  return (
    <div className="project-selector">
      <Dropdown
        id="project-selector-dropdown"
        titleText={label}
        label={loading ? 'Loading projects...' : 'Choose a project'}
        items={projects}
        itemToString={(item) => item ? `${item.name} (${item.document_count} docs)` : ''}
        selectedItem={selectedProject}
        onChange={handleChange}
        disabled={disabled || loading}
        invalid={!!error}
        invalidText={error}
      />
    </div>
  );
};

export default ProjectSelector;

// Made with Bob