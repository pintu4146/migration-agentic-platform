/**
 * AssistancePanel
 *
 * 4th tab in HumanReview.jsx — the Advanced Assistance ReAct chat interface.
 *
 * Features:
 *  - Real-time SSE streaming (word-by-word answer delivery)
 *  - Collapsible Thought/Action/Observation trace per message
 *  - File / text paste drop zone for context ingestion
 *  - "Run this command" copy-to-clipboard code block
 *  - IBM Carbon Design System throughout (explicit hex colors)
 *  - Loads conversation history from Redis on mount
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Button,
  TextArea,
  InlineNotification,
  Tag,
  IconButton,
} from '@carbon/react';
import {
  SendAlt,
  Close,
  ChevronDown,
  ChevronUp,
  Copy,
  TrashCan,
  DocumentAdd,
  Bot,
  User,
  Stop,
} from '@carbon/icons-react';
import useAssistance from '../../hooks/useAssistance';
import './AssistancePanel.scss';

// ── Sub-components ────────────────────────────────────────────────────────────

/**
 * Collapsible Thought/Action/Observation trace block.
 */
const TraceBlock = ({ trace }) => {
  const [open, setOpen] = useState(false);
  if (!trace || trace.length === 0) return null;

  const stepCount = trace.filter((t) => t.type === 'action').length;

  return (
    <div className="assistance-trace">
      <button
        className="assistance-trace__toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        <span>{stepCount} reasoning step{stepCount !== 1 ? 's' : ''}</span>
      </button>
      {open && (
        <div className="assistance-trace__body">
          {trace.map((step, i) => (
            <div key={i} className={`assistance-trace__step assistance-trace__step--${step.type}`}>
              {step.type === 'thought' && (
                <><span className="assistance-trace__label">Thought</span> {step.text}</>
              )}
              {step.type === 'action' && (
                <><span className="assistance-trace__label">Action</span>
                  <code className="assistance-trace__tool">{step.tool}</code>
                  <span className="assistance-trace__input"> ← {step.input}</span>
                </>
              )}
              {step.type === 'observation' && (
                <><span className="assistance-trace__label">Obs</span> {step.text?.slice(0, 300)}{step.text?.length > 300 ? '...' : ''}</>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

/**
 * Single chat message bubble.
 */
const MessageBubble = ({ message }) => {
  const isUser = message.role === 'user';
  const isStreaming = message.streaming;

  // Detect command blocks in assistant messages
  const renderContent = (content) => {
    if (!content) return null;
    // Split on ``` code blocks
    const parts = content.split(/(```[\s\S]*?```)/g);
    return parts.map((part, i) => {
      if (part.startsWith('```')) {
        const lines = part.split('\n');
        const lang = lines[0].replace('```', '').trim() || 'bash';
        const code = lines.slice(1, -1).join('\n');
        return (
          <div key={i} className="assistance-message__code-block">
            <div className="assistance-message__code-header">
              <span>{lang}</span>
              <IconButton
                label="Copy command"
                size="sm"
                kind="ghost"
                onClick={() => navigator.clipboard.writeText(code)}
              >
                <Copy size={14} />
              </IconButton>
            </div>
            <pre className="assistance-message__code">{code}</pre>
          </div>
        );
      }
      return <span key={i}>{part}</span>;
    });
  };

  return (
    <div className={`assistance-message assistance-message--${isUser ? 'user' : 'assistant'}`}>
      <div className="assistance-message__avatar">
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>
      <div className="assistance-message__body">
        <div className="assistance-message__content">
          {renderContent(message.content)}
          {isStreaming && <span className="assistance-message__cursor" aria-hidden="true">▌</span>}
          {message.error && (
            <span className="assistance-message__error-flag"> ⚠ Error</span>
          )}
        </div>
        {!isUser && message.trace && message.trace.length > 0 && (
          <TraceBlock trace={message.trace} />
        )}
        <div className="assistance-message__meta">
          {new Date(message.timestamp).toLocaleTimeString()}
          {message.fromHistory && <Tag size="sm" type="gray" className="assistance-message__hist-tag">History</Tag>}
        </div>
      </div>
    </div>
  );
};

// ── Main Panel ────────────────────────────────────────────────────────────────

/**
 * AssistancePanel — 4th tab in HumanReview.
 *
 * @param {string} projectId - Current project identifier
 */
const AssistancePanel = ({ projectId }) => {
  const {
    messages,
    isStreaming,
    currentThought,
    currentAction,
    error,
    sendMessage,
    ingest,
    clearChat,
    loadHistory,
    stopStreaming,
    setError,
  } = useAssistance(projectId);

  const [inputText, setInputText] = useState('');
  const [ingestText, setIngestText] = useState('');
  const [showIngest, setShowIngest] = useState(false);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [ingestSuccess, setIngestSuccess] = useState(false);
  const messagesEndRef = useRef(null);
  const textAreaRef = useRef(null);

  // Load history on mount
  useEffect(() => {
    if (projectId) loadHistory();
  }, [projectId, loadHistory]);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentThought, currentAction]);

  const handleSend = useCallback(() => {
    const text = inputText.trim();
    if (!text || isStreaming) return;
    setInputText('');
    sendMessage(text);
  }, [inputText, isStreaming, sendMessage]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  const handleIngest = useCallback(async () => {
    if (!ingestText.trim()) return;
    setIngestLoading(true);
    try {
      await ingest(ingestText, 'user_note', 'Manual paste');
      setIngestSuccess(true);
      setIngestText('');
      setTimeout(() => setIngestSuccess(false), 3000);
    } catch {
      // error set in hook
    } finally {
      setIngestLoading(false);
    }
  }, [ingestText, ingest]);

  return (
    <div className="assistance-panel">
      {/* Header */}
      <div className="assistance-panel__header">
        <div className="assistance-panel__header-left">
          <Bot size={20} className="assistance-panel__bot-icon" />
          <div>
            <h3 className="assistance-panel__title">Advanced Assistant</h3>
            <p className="assistance-panel__subtitle">
              ReAct agent · searches extracted facts, project documents &amp; generates commands
            </p>
          </div>
        </div>
        <div className="assistance-panel__header-actions">
          <Button
            kind="ghost"
            size="sm"
            renderIcon={DocumentAdd}
            onClick={() => setShowIngest((v) => !v)}
            iconDescription="Paste context"
          >
            Paste Context
          </Button>
          <IconButton
            label="Clear chat"
            kind="ghost"
            size="sm"
            onClick={clearChat}
          >
            <TrashCan size={16} />
          </IconButton>
        </div>
      </div>

      {/* Ingest drop zone */}
      {showIngest && (
        <div className="assistance-panel__ingest">
          <p className="assistance-panel__ingest-label">
            Paste command output or documentation to add to the project knowledge base:
          </p>
          <TextArea
            id="ingest-text"
            labelText=""
            placeholder="Paste command output, config snippets, or additional docs here..."
            value={ingestText}
            onChange={(e) => setIngestText(e.target.value)}
            rows={4}
          />
          <div className="assistance-panel__ingest-actions">
            <Button
              kind="primary"
              size="sm"
              onClick={handleIngest}
              disabled={!ingestText.trim() || ingestLoading}
            >
              {ingestLoading ? 'Storing...' : 'Store in Knowledge Base'}
            </Button>
            <Button kind="ghost" size="sm" onClick={() => setShowIngest(false)}>
              Cancel
            </Button>
          </div>
          {ingestSuccess && (
            <InlineNotification
              kind="success"
              title="Stored"
              subtitle="Content added to project knowledge base."
              lowContrast
              onCloseButtonClick={() => setIngestSuccess(false)}
            />
          )}
        </div>
      )}

      {/* Error banner */}
      {error && (
        <InlineNotification
          kind="error"
          title="Assistant error"
          subtitle={error}
          lowContrast
          onCloseButtonClick={() => setError(null)}
        />
      )}

      {/* Messages list */}
      <div className="assistance-panel__messages" role="log" aria-live="polite">
        {messages.length === 0 && !isStreaming && (
          <div className="assistance-panel__empty">
            <Bot size={32} className="assistance-panel__empty-icon" />
            <p>Ask me anything about the extracted facts, validation results, or migration plan.</p>
            <div className="assistance-panel__suggestions">
              {[
                'Why was the database dependency flagged?',
                'What is the confidence score for spring-security?',
                'Generate a command to list all Maven dependencies',
              ].map((s) => (
                <button
                  key={s}
                  className="assistance-panel__suggestion"
                  onClick={() => sendMessage(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {/* Live streaming indicator */}
        {isStreaming && (currentThought || currentAction) && (
          <div className="assistance-panel__streaming-indicator">
            {currentThought && (
              <div className="assistance-panel__live-thought">
                <span className="assistance-panel__live-label">Thinking</span>
                {currentThought}
              </div>
            )}
            {currentAction && (
              <div className="assistance-panel__live-action">
                <span className="assistance-panel__live-label">Using tool</span>
                <code>{currentAction.tool}</code>
              </div>
            )}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="assistance-panel__input-area">
        <TextArea
          ref={textAreaRef}
          id="assistance-input"
          labelText=""
          placeholder="Ask about the intake draft, validation results, or dependencies..."
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={2}
          disabled={isStreaming}
          aria-label="Chat message input"
        />
        <div className="assistance-panel__input-actions">
          <span className="assistance-panel__hint">Shift+Enter for new line · Enter to send</span>
          <div className="assistance-panel__input-buttons">
            {isStreaming && (
              <Button kind="ghost" size="sm" renderIcon={Stop} onClick={stopStreaming}>
                Stop
              </Button>
            )}
            <Button
              kind="primary"
              size="sm"
              renderIcon={SendAlt}
              onClick={handleSend}
              disabled={!inputText.trim() || isStreaming}
              aria-label="Send message"
            >
              {isStreaming ? 'Thinking...' : 'Send'}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AssistancePanel;

// Made with Bob
