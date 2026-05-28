/**
 * Workflow Helper Functions
 * 
 * Utilities for processing workflow state and building UI data
 */

/**
 * Get list of completed phases based on current phase
 */
export const getCompletedPhases = (state) => {
  if (!state) return [];
  
  const phaseOrder = [
    'init',
    'context_retrieval',
    'extraction',
    'questionnaire',
    'intake_draft',
    'human_review',
    'migration_planning',
    'validation',
    'complete'
  ];
  
  const currentIndex = phaseOrder.indexOf(state.phase);
  return currentIndex > 0 ? phaseOrder.slice(0, currentIndex) : [];
};

/**
 * Get current phase status
 */
export const getPhaseStatus = (state) => {
  if (!state) return 'unknown';
  
  if (state.phase === 'complete') return 'completed';
  if (state.phase === 'human_review' && !state.human_reviewed) return 'paused';
  if (state.phase === 'error' || state.last_error) return 'error';
  return 'in_progress';
};

/**
 * Get phase display name
 */
export const getPhaseDisplayName = (phase) => {
  const names = {
    'init': 'Initialize',
    'context_retrieval': 'Retrieve Context',
    'extraction': 'Extract Facts',
    'questionnaire': 'Generate Questions',
    'intake_draft': 'Draft Intake',
    'human_review': 'Human Review',
    'migration_planning': 'Plan Migration',
    'validation': 'Validate',
    'complete': 'Complete'
  };
  return names[phase] || phase;
};

/**
 * Get phase description
 */
export const getPhaseDescription = (phase) => {
  const descriptions = {
    'init': 'Starting workflow',
    'context_retrieval': 'Fetching documents from MCP and Qdrant',
    'extraction': 'Using AI to extract technical facts',
    'questionnaire': 'Analyzing gaps and generating questions',
    'intake_draft': 'Creating structured intake document',
    'human_review': 'Waiting for human review and approval',
    'migration_planning': 'Generating migration strategy',
    'validation': 'Validating final output',
    'complete': 'Workflow finished'
  };
  return descriptions[phase] || 'Processing...';
};

/**
 * Build activity log from workflow state
 */
export const buildActivityLog = (state) => {
  if (!state?.trace_metadata) return [];
  
  const activities = [];
  const metadata = state.trace_metadata;
  
  // Add initialization
  if (metadata.initialized_at) {
    activities.push({
      timestamp: metadata.initialized_at,
      message: `Workflow initialized for project: ${state.project_id}`,
      status: 'success',
      phase: 'init'
    });
  }
  
  // Add context retrieval
  if (metadata.context_retrieval) {
    const cr = metadata.context_retrieval;
    activities.push({
      timestamp: cr.timestamp,
      message: `Retrieved ${cr.documents_retrieved} documents from ${cr.source_used}`,
      status: 'success',
      phase: 'context_retrieval',
      details: cr
    });
    
    // Add source attempts if available
    if (cr.sources_tried) {
      cr.sources_tried.forEach(source => {
        if (source.includes('no documents')) {
          activities.push({
            timestamp: cr.timestamp,
            message: source,
            status: 'warning',
            phase: 'context_retrieval'
          });
        }
      });
    }
  }
  
  // Add extraction
  if (metadata.extraction) {
    const ex = metadata.extraction;
    activities.push({
      timestamp: ex.timestamp,
      message: `Extracted ${ex.facts_extracted} facts (${(ex.avg_confidence * 100).toFixed(0)}% avg confidence)`,
      status: 'success',
      phase: 'extraction',
      details: ex
    });
  }
  
  // Add questionnaire
  if (metadata.questionnaire) {
    const q = metadata.questionnaire;
    activities.push({
      timestamp: q.timestamp,
      message: `Generated ${q.questions_generated} questions (${q.high_priority_count} high priority)`,
      status: 'success',
      phase: 'questionnaire',
      details: q
    });
  }
  
  // Add current phase status
  if (state.phase === 'human_review' && !state.human_reviewed) {
    activities.push({
      timestamp: state.updated_at || new Date().toISOString(),
      message: 'Workflow paused for human review',
      status: 'paused',
      phase: 'human_review'
    });
  }
  
  // Add errors if any
  if (state.last_error) {
    activities.push({
      timestamp: state.updated_at || new Date().toISOString(),
      message: `Error: ${state.last_error}`,
      status: 'error',
      phase: state.phase
    });
  }
  
  // Sort by timestamp (most recent first)
  return activities.sort((a, b) => 
    new Date(b.timestamp) - new Date(a.timestamp)
  );
};

/**
 * Extract phase data for status cards
 */
export const extractPhaseData = (state) => {
  if (!state?.trace_metadata) return {};
  
  const metadata = state.trace_metadata;
  
  return {
    context: {
      documents_count: metadata.context_retrieval?.documents_retrieved || 0,
      source: metadata.context_retrieval?.source_used || 'unknown',
      timestamp: metadata.context_retrieval?.timestamp
    },
    extraction: {
      facts_count: metadata.extraction?.facts_extracted || 0,
      avg_confidence: metadata.extraction?.avg_confidence || 0,
      categories: metadata.extraction?.categories?.length || 0,
      timestamp: metadata.extraction?.timestamp
    },
    questionnaire: {
      questions_count: metadata.questionnaire?.questions_generated || 0,
      high_priority_count: metadata.questionnaire?.high_priority_count || 0,
      low_confidence_facts: metadata.questionnaire?.low_confidence_facts || 0,
      missing_fields: metadata.questionnaire?.missing_fields || 0,
      timestamp: metadata.questionnaire?.timestamp
    }
  };
};

/**
 * Format timestamp for display
 */
export const formatTimestamp = (timestamp) => {
  if (!timestamp) return '';
  
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    });
  } catch (e) {
    return timestamp;
  }
};

/**
 * Calculate workflow duration
 */
export const calculateDuration = (state) => {
  if (!state?.created_at || !state?.updated_at) return null;
  
  try {
    const start = new Date(state.created_at);
    const end = new Date(state.updated_at);
    const diffMs = end - start;
    const diffSecs = Math.floor(diffMs / 1000);
    
    if (diffSecs < 60) {
      return `${diffSecs}s`;
    } else if (diffSecs < 3600) {
      const mins = Math.floor(diffSecs / 60);
      const secs = diffSecs % 60;
      return `${mins}m ${secs}s`;
    } else {
      const hours = Math.floor(diffSecs / 3600);
      const mins = Math.floor((diffSecs % 3600) / 60);
      return `${hours}h ${mins}m`;
    }
  } catch (e) {
    return null;
  }
};

/**
 * Get status badge configuration
 */
export const getStatusBadge = (status) => {
  const badges = {
    'in_progress': { text: 'In Progress', kind: 'blue' },
    'paused': { text: 'Paused', kind: 'yellow' },
    'completed': { text: 'Completed', kind: 'green' },
    'error': { text: 'Error', kind: 'red' },
    'unknown': { text: 'Unknown', kind: 'gray' }
  };
  return badges[status] || badges['unknown'];
};

/**
 * Get progress percentage
 */
export const getProgressPercentage = (state) => {
  if (!state) return 0;
  
  const phaseWeights = {
    'init': 5,
    'context_retrieval': 15,
    'extraction': 30,
    'questionnaire': 15,
    'intake_draft': 10,
    'human_review': 10,
    'migration_planning': 10,
    'validation': 5,
    'complete': 0
  };
  
  const phaseOrder = Object.keys(phaseWeights);
  const currentIndex = phaseOrder.indexOf(state.phase);
  
  if (currentIndex === -1) return 0;
  if (state.phase === 'complete') return 100;
  
  // Sum weights of completed phases
  let progress = 0;
  for (let i = 0; i < currentIndex; i++) {
    progress += phaseWeights[phaseOrder[i]];
  }
  
  return progress;
};

// Made with Bob
