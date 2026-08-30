import { useState, useCallback, useRef } from 'react';
import { streamChat, ingestContext, getHistory, clearHistory } from '../services/assistanceApi';

/**
 * useAssistance — Custom hook for the Advanced Assistance panel.
 *
 * Manages:
 *  - messages array (user + assistant with trace metadata)
 *  - streaming state (isStreaming, currentThought, currentAction)
 *  - conversation history load/clear
 *  - context ingestion
 *  - error state
 *
 * @param {string} projectId - Project identifier
 * @returns {Object} Hook state and handlers
 */
const useAssistance = (projectId) => {
  // ── State ──────────────────────────────────────────────────────────────────
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentThought, setCurrentThought] = useState('');
  const [currentAction, setCurrentAction] = useState(null);
  const [currentObservation, setCurrentObservation] = useState('');
  const [partialAnswer, setPartialAnswer] = useState('');
  const [error, setError] = useState(null);
  const [historyLoaded, setHistoryLoaded] = useState(false);

  // Refs for aborting mid-stream
  const abortRef = useRef(false);
  const streamingMsgIdRef = useRef(null);

  // ── Load history on first open ─────────────────────────────────────────────
  const loadHistory = useCallback(async () => {
    if (!projectId || historyLoaded) return;
    try {
      const result = await getHistory(projectId, 30);
      const loaded = (result.messages || []).map((m, i) => ({
        id: `hist-${i}`,
        role: m.role,
        content: m.content,
        timestamp: m.timestamp,
        metadata: m.metadata || null,
        fromHistory: true,
      }));
      setMessages(loaded);
      setHistoryLoaded(true);
    } catch (err) {
      // Non-fatal — fresh start if history unavailable
      console.warn('useAssistance: could not load history —', err.message);
      setHistoryLoaded(true);
    }
  }, [projectId, historyLoaded]);

  // ── Send a message ─────────────────────────────────────────────────────────
  const sendMessage = useCallback(async (text) => {
    if (!text.trim() || isStreaming || !projectId) return;

    setError(null);
    abortRef.current = false;

    // Append user message immediately
    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    // Placeholder for streaming assistant reply
    const assistantMsgId = `assistant-${Date.now()}`;
    streamingMsgIdRef.current = assistantMsgId;
    setMessages((prev) => [
      ...prev,
      {
        id: assistantMsgId,
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString(),
        streaming: true,
        trace: [],
      },
    ]);

    setIsStreaming(true);
    setCurrentThought('');
    setCurrentAction(null);
    setCurrentObservation('');
    setPartialAnswer('');

    try {
      for await (const { event, data } of streamChat(projectId, text)) {
        if (abortRef.current) break;

        switch (event) {
          case 'thought':
            setCurrentThought(data.text || '');
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? { ...m, trace: [...(m.trace || []), { type: 'thought', text: data.text }] }
                  : m
              )
            );
            break;

          case 'action':
            setCurrentAction({ tool: data.tool, input: data.input });
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? { ...m, trace: [...(m.trace || []), { type: 'action', tool: data.tool, input: data.input }] }
                  : m
              )
            );
            break;

          case 'observation':
            setCurrentObservation(data.text || '');
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? { ...m, trace: [...(m.trace || []), { type: 'observation', text: data.text }] }
                  : m
              )
            );
            break;

          case 'answer':
            setPartialAnswer((prev) => prev + (data.text || ''));
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? { ...m, content: m.content + (data.text || '') }
                  : m
              )
            );
            break;

          case 'error':
            setError(data.message || 'An error occurred.');
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId
                  ? { ...m, streaming: false, error: true, content: m.content || 'Error: ' + data.message }
                  : m
              )
            );
            break;

          case 'done':
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantMsgId ? { ...m, streaming: false } : m
              )
            );
            break;

          default:
            break;
        }
      }
    } catch (err) {
      setError(err.message || 'Chat request failed');
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMsgId
            ? { ...m, streaming: false, error: true, content: m.content || 'Connection error.' }
            : m
        )
      );
    } finally {
      setIsStreaming(false);
      setCurrentThought('');
      setCurrentAction(null);
      setCurrentObservation('');
      setPartialAnswer('');
      streamingMsgIdRef.current = null;
    }
  }, [projectId, isStreaming]);

  // ── Ingest context ─────────────────────────────────────────────────────────
  const ingest = useCallback(async (text, contextType = 'user_note', sourceLabel = null) => {
    try {
      const result = await ingestContext(projectId, text, contextType, sourceLabel);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  }, [projectId]);

  // ── Clear history ──────────────────────────────────────────────────────────
  const clearChat = useCallback(async () => {
    try {
      await clearHistory(projectId);
      setMessages([]);
      setHistoryLoaded(false);
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, [projectId]);

  // ── Stop streaming ─────────────────────────────────────────────────────────
  const stopStreaming = useCallback(() => {
    abortRef.current = true;
    setIsStreaming(false);
  }, []);

  return {
    messages,
    isStreaming,
    currentThought,
    currentAction,
    currentObservation,
    error,
    sendMessage,
    ingest,
    clearChat,
    loadHistory,
    stopStreaming,
    setError,
  };
};

export default useAssistance;

// Made with Bob
