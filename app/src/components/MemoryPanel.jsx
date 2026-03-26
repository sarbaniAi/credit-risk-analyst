import React, { useState, useEffect } from 'react';
import { getUserMemories, clearUserMemories, getUserId } from '../services/agentService';
import './MemoryPanel.css';

const BrainIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
    <path d="M12 2a9 9 0 0 0-9 9c0 4.17 2.84 7.67 6.69 8.69L12 22l2.31-2.31C18.16 18.67 21 15.17 21 11a9 9 0 0 0-9-9zm0 16c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z"/>
    <circle cx="12" cy="11" r="3"/>
  </svg>
);

const ClockIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
  </svg>
);

const TrashIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
    <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
  </svg>
);

const RefreshIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
    <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
  </svg>
);

const UserIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
    <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
  </svg>
);

function MemoryPanel({ isOpen, onClose }) {
  const [memories, setMemories] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [clearing, setClearing] = useState(false);

  const loadMemories = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getUserMemories();
      setMemories(data.memories || []);
      setConversations(data.conversations || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClearMemories = async () => {
    if (!confirm('Are you sure you want to clear all your memories? This cannot be undone.')) {
      return;
    }
    setClearing(true);
    try {
      await clearUserMemories();
      setMemories([]);
      setConversations([]);
    } catch (e) {
      setError(e.message);
    } finally {
      setClearing(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadMemories();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="memory-panel-overlay" onClick={onClose}>
      <div className="memory-panel" onClick={e => e.stopPropagation()}>
        <div className="memory-panel-header">
          <div className="memory-panel-title">
            <BrainIcon />
            <h2>Agent Memory</h2>
          </div>
          <div className="memory-panel-actions">
            <button className="action-btn" onClick={loadMemories} disabled={loading} title="Refresh">
              <RefreshIcon />
            </button>
            <button className="action-btn danger" onClick={handleClearMemories} disabled={clearing} title="Clear All">
              <TrashIcon />
            </button>
            <button className="close-btn" onClick={onClose}>×</button>
          </div>
        </div>

        <div className="memory-panel-user">
          <UserIcon />
          <span>{getUserId()}</span>
        </div>

        <div className="memory-panel-content">
          {loading && (
            <div className="memory-loading">
              <div className="spinner"></div>
              <span>Loading memories...</span>
            </div>
          )}

          {error && (
            <div className="memory-error">
              <p>Error: {error}</p>
              <button onClick={loadMemories}>Retry</button>
            </div>
          )}

          {!loading && !error && (
            <>
              <section className="memory-section">
                <h3>Long-term Memories</h3>
                {memories.length === 0 ? (
                  <p className="empty-state">No memories stored yet. As you chat, the agent will learn and remember key insights.</p>
                ) : (
                  <div className="memory-list">
                    {memories.map((mem, idx) => (
                      <div key={idx} className="memory-item">
                        <div className="memory-item-header">
                          <span className="memory-type">{mem.memory_type}</span>
                          <span className="memory-key">{mem.memory_key}</span>
                        </div>
                        <div className="memory-value">{mem.memory_value}</div>
                        <div className="memory-time">
                          <ClockIcon />
                          {new Date(mem.updated_at).toLocaleString()}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section className="memory-section">
                <h3>Recent Conversations</h3>
                {conversations.length === 0 ? (
                  <p className="empty-state">No conversation history yet.</p>
                ) : (
                  <div className="conversation-list">
                    {conversations.map((conv, idx) => (
                      <div key={idx} className="conversation-item">
                        <div className="conversation-summary">{conv.summary}</div>
                        {conv.customer_ids && conv.customer_ids.length > 0 && (
                          <div className="conversation-customers">
                            Customers: {conv.customer_ids.join(', ')}
                          </div>
                        )}
                        <div className="conversation-time">
                          <ClockIcon />
                          {new Date(conv.created_at).toLocaleString()}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default MemoryPanel;
