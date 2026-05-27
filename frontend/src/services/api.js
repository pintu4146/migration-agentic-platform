import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Document Upload API
export const uploadDocument = async (file, projectId) => {
  const formData = new FormData();
  formData.append('file', file);
  if (projectId) {
    formData.append('project_id', projectId);
  }

  const response = await api.post('/api/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const searchDocuments = async (projectId, query, limit = 10) => {
  const response = await api.post('/api/documents/search', {
    project_id: projectId,
    query,
    limit,
  });
  return response.data;
};

export const listDocuments = async (projectId) => {
  const response = await api.get(`/api/documents/list/${projectId}`);
  return response.data;
};

export const deleteDocument = async (documentId) => {
  const response = await api.delete(`/api/documents/${documentId}`);
  return response.data;
};

// Workflow Orchestration API
export const startWorkflow = async (projectId, mcpProfile = 'context_retrieval_profile', query = null) => {
  const response = await api.post('/api/orchestration/start', {
    project_id: projectId,
    mcp_profile: mcpProfile,
    query,
  });
  return response.data;
};

export const executeWorkflow = async (projectId) => {
  const response = await api.post('/api/orchestration/execute', {
    project_id: projectId,
  });
  return response.data;
};

export const getWorkflowState = async (projectId) => {
  const response = await api.get(`/api/orchestration/state/${projectId}`);
  return response.data;
};

export const resumeWorkflow = async (projectId, updates = null) => {
  const response = await api.post('/api/orchestration/resume', {
    project_id: projectId,
    updates,
  });
  return response.data;
};

// MCP API
export const checkMCPHealth = async () => {
  const response = await api.get('/mcp/health');
  return response.data;
};

export const retrieveContext = async (projectId, profile = 'extraction_profile') => {
  const response = await api.post('/mcp/retrieve', {
    project_id: projectId,
    profile,
  });
  return response.data;
};

export default api;

// Made with Bob
