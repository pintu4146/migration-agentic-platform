/**
 * Custom Hook: useWorkflowSSE
 * 
 * Uses Server-Sent Events (SSE) for real-time workflow state updates
 * Replaces polling with efficient push-based updates
 */

import { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Hook to receive real-time workflow state updates via SSE
 * 
 * @param {string} projectId - Project ID to monitor
 * @param {boolean} isActive - Whether SSE connection is active
 * @returns {object} - { state, loading, error, isConnected, refetch }
 */
export const useWorkflowSSE = (projectId, isActive = true) => {
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [phaseInfo, setPhaseInfo] = useState(null);
  const [phaseTransition, setPhaseTransition] = useState(null);
  const eventSourceRef = useRef(null);
  const mountedRef = useRef(true);
  const reconnectTimeoutRef = useRef(null);

  const cleanup = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const connect = useCallback(() => {
    if (!projectId || !isActive || !mountedRef.current) {
      return;
    }

    // Clean up existing connection
    cleanup();

    try {
      const url = `${API_BASE_URL}/api/orchestration/stream/${projectId}`;
      console.log(`SSE: Connecting to ${url}`);
      
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        if (mountedRef.current) {
          console.log(`SSE: Connected to ${projectId}`);
          setIsConnected(true);
          setError(null);
          setLoading(false);
        }
      };

      eventSource.addEventListener('state_update', (event) => {
        if (mountedRef.current) {
          try {
            const data = JSON.parse(event.data);
            console.log(`SSE: Received state update for ${projectId}`, data);
            
            // Handle enriched event data
            if (data.state && data.phase_info) {
              setState(data.state);
              setPhaseInfo(data.phase_info);
              console.log(`SSE: Phase info:`, data.phase_info);
            } else {
              // Fallback for old format
              setState(data);
            }
            setError(null);
          } catch (err) {
            console.error('SSE: Failed to parse state update:', err);
            setError('Failed to parse state update');
          }
        }
      });

      eventSource.addEventListener('phase_transition', (event) => {
        if (mountedRef.current) {
          try {
            const transition = JSON.parse(event.data);
            console.log(`SSE: Phase transition ${transition.from_phase} → ${transition.to_phase}`);
            setPhaseTransition(transition);
            
            // Clear transition after 3 seconds
            setTimeout(() => {
              if (mountedRef.current) {
                setPhaseTransition(null);
              }
            }, 3000);
          } catch (err) {
            console.error('SSE: Failed to parse phase transition:', err);
          }
        }
      });

      eventSource.addEventListener('error', (event) => {
        if (mountedRef.current) {
          try {
            const errorData = JSON.parse(event.data);
            console.error('SSE: Server error:', errorData);
            setError(errorData.error || 'Server error');
          } catch (err) {
            console.error('SSE: Failed to parse error event:', err);
          }
        }
      });

      eventSource.onerror = (err) => {
        console.error('SSE: Connection error:', err);
        
        if (mountedRef.current) {
          setIsConnected(false);
          setError('Connection lost');
          
          // Attempt to reconnect after 5 seconds
          reconnectTimeoutRef.current = setTimeout(() => {
            if (mountedRef.current && isActive) {
              console.log('SSE: Attempting to reconnect...');
              connect();
            }
          }, 5000);
        }
        
        cleanup();
      };

    } catch (err) {
      console.error('SSE: Failed to create EventSource:', err);
      if (mountedRef.current) {
        setError('Failed to establish connection');
        setLoading(false);
      }
    }
  }, [projectId, isActive, cleanup]);

  // Manual refetch function (for compatibility with existing code)
  const refetch = useCallback(() => {
    console.log('SSE: Manual refetch requested - reconnecting');
    connect();
  }, [connect]);

  useEffect(() => {
    mountedRef.current = true;
    
    if (projectId && isActive) {
      connect();
    }

    return () => {
      mountedRef.current = false;
      cleanup();
    };
  }, [projectId, isActive, connect, cleanup]);

  return {
    state,
    loading,
    error,
    isConnected,
    phaseInfo,
    phaseTransition,
    refetch
  };
};

export default useWorkflowSSE;

// Made with Bob