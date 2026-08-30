/**
 * Assistance API Service
 *
 * All HTTP calls to the Advanced Assistance microservice (:8001).
 * Proxied via Vite: /api/assistance → http://localhost:8001
 *
 * Endpoints:
 *   streamChat   — QUERY /api/assistance/chat/{projectId}  (SSE stream)
 *   ingestContext— POST  /api/assistance/context/{projectId}
 *   getHistory   — GET   /api/assistance/history/{projectId}
 *   clearHistory — DELETE /api/assistance/history/{projectId}
 */

const ASSISTANCE_BASE = '/api/assistance';

// ── Streaming chat ────────────────────────────────────────────────────────────

/**
 * Stream a chat response from the ReAct agent via SSE.
 *
 * Tries QUERY method first (safe + idempotent with body).
 * Falls back to POST automatically if QUERY is rejected (405).
 *
 * @param {string} projectId - Project identifier
 * @param {string} message   - User message
 * @yields {Object} SSE event objects: { event, data }
 */
export async function* streamChat(projectId, message) {
  const url = `${ASSISTANCE_BASE}/chat/${projectId}`;
  const body = JSON.stringify({ message, project_id: projectId });
  const headers = { 'Content-Type': 'application/json' };

  let response;

  // Try QUERY method first
  try {
    response = await fetch(url, { method: 'QUERY', headers, body });
    if (response.status === 405) throw new Error('QUERY not supported');
  } catch {
    // Fallback to POST
    response = await fetch(url, { method: 'POST', headers, body });
  }

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`Chat request failed: ${response.status} — ${errText}`);
  }

  if (!response.body) {
    throw new Error('No readable stream in response');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Split on double-newline SSE boundaries
    const parts = buffer.split('\n\n');
    buffer = parts.pop() ?? ''; // keep incomplete chunk

    for (const part of parts) {
      if (!part.trim()) continue;

      let event = 'message';
      let dataStr = '';

      for (const line of part.split('\n')) {
        if (line.startsWith('event: ')) {
          event = line.slice(7).trim();
        } else if (line.startsWith('data: ')) {
          dataStr = line.slice(6).trim();
        }
      }

      if (!dataStr) continue;

      try {
        const data = JSON.parse(dataStr);
        yield { event, data };
      } catch {
        yield { event, data: { text: dataStr } };
      }
    }
  }
}

// ── Context ingestion ─────────────────────────────────────────────────────────

/**
 * Ingest user-provided text (command output, doc paste) into project knowledge base.
 *
 * @param {string} projectId    - Project identifier
 * @param {string} text         - Text content to store
 * @param {string} contextType  - 'command_output' | 'user_note' | 'doc_paste'
 * @param {string} [sourceLabel]- Human-readable label
 * @returns {Promise<Object>}   - { project_id, chunks_added, message }
 */
export const ingestContext = async (projectId, text, contextType = 'user_note', sourceLabel = null) => {
  const response = await fetch(`${ASSISTANCE_BASE}/context/${projectId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text,
      context_type: contextType,
      source_label: sourceLabel,
    }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(err.detail || 'Context ingestion failed');
  }

  return response.json();
};

// ── History ───────────────────────────────────────────────────────────────────

/**
 * Retrieve conversation history for a project.
 *
 * @param {string} projectId - Project identifier
 * @param {number} [lastN=20]- Number of recent messages
 * @returns {Promise<Object>} - { project_id, messages, count, total_stored }
 */
export const getHistory = async (projectId, lastN = 20) => {
  const response = await fetch(
    `${ASSISTANCE_BASE}/history/${projectId}?last_n=${lastN}`
  );

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(err.detail || 'Failed to load history');
  }

  return response.json();
};

/**
 * Clear all conversation history for a project.
 *
 * @param {string} projectId - Project identifier
 * @returns {Promise<Object>} - { project_id, cleared, message }
 */
export const clearHistory = async (projectId) => {
  const response = await fetch(`${ASSISTANCE_BASE}/history/${projectId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(err.detail || 'Failed to clear history');
  }

  return response.json();
};

// ── Health ────────────────────────────────────────────────────────────────────

/**
 * Check assistance service health.
 * @returns {Promise<Object>} - { status, service, timestamp }
 */
export const checkAssistanceHealth = async () => {
  const response = await fetch('/api/assistance/health');
  if (!response.ok) throw new Error('Assistance service unhealthy');
  return response.json();
};

// Made with Bob
