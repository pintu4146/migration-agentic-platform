/**
 * Custom Hook: useWorkflowPolling
 * 
 * Polls workflow state at regular intervals to keep UI in sync with backend
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { getWorkflowState } from '../services/api';

/**
 * Hook to poll workflow state
 * 
 * @param {string} projectId - Project ID to poll
 * @param {boolean} isActive - Whether polling is active
 * @param {number} interval - Polling interval in milliseconds (default: 2000)
 * @returns {object} - { state, loading, error, refetch, isPolling }
 */
export const useWorkflowPolling = (projectId, isActive = true, interval = 2000) => {
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isPolling, setIsPolling] = useState(false);
  const intervalRef = useRef(null);
  const mountedRef = useRef(true);

  const fetchState = useCallback(async () => {
    if (!projectId || !isActive || !mountedRef.current) return;
    
    try {
      const response = await getWorkflowState(projectId);
      
      if (mountedRef.current) {
        // API returns data directly, not wrapped in response.data
        setState(response);
        setError(null);
        setIsPolling(true);
      }
    } catch (err) {
      console.error('Failed to fetch workflow state:', err);
      
      if (mountedRef.current) {
        // Only set error if it's not a 404 (project not started yet)
        if (err.response?.status !== 404) {
          setError(err.response?.data?.detail || err.message || 'Failed to fetch workflow state');
          setIsPolling(false);
        } else {
          // 404 means workflow not started yet - not an error
          setState(null);
          setIsPolling(false);
        }
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [projectId, isActive]);

  useEffect(() => {
    mountedRef.current = true;
    
    // Initial fetch
    fetchState();

    // Set up polling if active
    if (isActive && projectId) {
      intervalRef.current = setInterval(fetchState, interval);
    }

    // Cleanup
    return () => {
      mountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [fetchState, isActive, projectId, interval]);

  return {
    state,
    loading,
    error,
    refetch: fetchState,
    isPolling
  };
};

export default useWorkflowPolling;

// Made with Bob
