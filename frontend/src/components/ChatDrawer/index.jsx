import React, { useState, useRef, useEffect } from 'react';
import { Button, TextInput, IconButton, InlineLoading } from '@carbon/react';
import { Close, Send } from '@carbon/icons-react';
import './ChatDrawer.scss';

/**
 * ChatDrawer — Slide-in assistant chat panel.
 *
 * MOCK_MODE = true: uses local mock replies with a simulated delay.
 * MOCK_MODE = false: swap the setTimeout block for a real SSE stream call
 *   e.g. const reply = await assistanceApi.sendMessage(projectId, text)
 *
 * Props:
 *   isOpen    {boolean}  Controls whether the drawer is visible
 *   onClose   {function} Called when the user closes the drawer
 *   projectId {string}   Current project ID (passed to real API when ready)
 */

// ─── Mock configuration ──────────────────────────────────────────────────────
const MOCK_MODE = true;

const MOCK_REPLIES = [
  'Based on the extracted facts, the application uses Spring Boot 2.7 with a PostgreSQL 13 database. The confidence score for the tech stack section is 0.92.',
  'The validation found 2 medium-priority flags related to missing deployment configuration. You can see the full details in the Review Flags tab.',
  "I don't have enough context to answer that with high confidence. Try running: mvn dependency:tree -Doutput=dep-tree.txt in your project root and paste the output here.",
];
// ─────────────────────────────────────────────────────────────────────────────

const ChatDrawer = ({ isOpen, onClose, projectId }) => {
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom whenever messages or thinking state change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking]);

  // Trap focus inside drawer when open (accessibility)
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  const handleSend = async () => {
    const text = inputText.trim();
    if (!text || isThinking) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      text,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputText('');
    setIsThinking(true);

    if (MOCK_MODE) {
      // ── Mock path: rotate through 3 canned replies ──────────────────────
      setTimeout(() => {
        const replyText = MOCK_REPLIES[messages.length % MOCK_REPLIES.length];
        setMessages(prev => [
          ...prev,
          {
            id: Date.now() + 1,
            role: 'assistant',
            text: replyText,
            timestamp: new Date().toISOString(),
          },
        ]);
        setIsThinking(false);
      }, 800);
    } else {
      // ── Real path: replace with assistanceApi.sendMessage() ─────────────
      // Example:
      // try {
      //   const reply = await assistanceApi.sendMessage(projectId, text);
      //   setMessages(prev => [...prev, { id: Date.now() + 1, role: 'assistant', text: reply, timestamp: new Date().toISOString() }]);
      // } catch (err) {
      //   setMessages(prev => [...prev, { id: Date.now() + 1, role: 'assistant', text: 'Sorry, something went wrong. Please try again.', timestamp: new Date().toISOString() }]);
      // } finally {
      //   setIsThinking(false);
      // }
    }
  };

  const handleKeyDown = e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const formatTime = isoString =>
    new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <>
      {/* Backdrop — click to close */}
      {isOpen && (
        <div
          className="chat-drawer__backdrop"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Drawer panel */}
      <div
        className={`chat-drawer${isOpen ? ' chat-drawer--open' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label="Assistant chat"
      >
        {/* Header */}
        <div className="chat-drawer__header">
          <span className="chat-drawer__title">Ask the Assistant</span>
          <IconButton
            label="Close assistant"
            onClick={onClose}
            kind="ghost"
            size="sm"
            className="chat-drawer__close-btn"
          >
            <Close />
          </IconButton>
        </div>

        {/* Messages */}
        <div className="chat-drawer__messages">
          {messages.length === 0 && !isThinking && (
            <div className="chat-drawer__empty-state">
              <p>Ask anything about this project — extracted facts, validation flags, dependencies, or migration risks.</p>
            </div>
          )}

          {messages.map(msg => (
            <div
              key={msg.id}
              className={`chat-drawer__message chat-drawer__message--${msg.role}`}
            >
              <span className="chat-drawer__message-text">{msg.text}</span>
              <span className="chat-drawer__message-time">{formatTime(msg.timestamp)}</span>
            </div>
          ))}

          {isThinking && (
            <div className="chat-drawer__message chat-drawer__message--assistant">
              <InlineLoading description="Thinking…" />
            </div>
          )}

          {/* Scroll anchor */}
          <div ref={messagesEndRef} />
        </div>

        {/* Input bar */}
        <div className="chat-drawer__input-bar">
          <TextInput
            id={`chat-input-${projectId}`}
            labelText=""
            hideLabel
            placeholder="Ask about this project…"
            value={inputText}
            onChange={e => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isThinking}
          />
          <Button
            kind="primary"
            size="md"
            renderIcon={Send}
            iconDescription="Send message"
            onClick={handleSend}
            disabled={isThinking || !inputText.trim()}
          >
            Send
          </Button>
        </div>
      </div>
    </>
  );
};

export default ChatDrawer;

// Made with Bob
