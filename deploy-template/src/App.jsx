import { useState, useEffect, useRef } from 'react';
import ChatMessage from './components/ChatMessage';
import MemoryPanel from './components/MemoryPanel';
import {
  callAgent,
  generateThreadId,
  saveToken,
  getToken,
  hasToken,
  clearToken,
  saveUserId,
  getUserId,
  hasUserId,
  clearUserMemories,
  getUserThreads,
  getThreadHistory,
} from './services/agentService';
import './App.css';

// SVG Icons
const DatabricksIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="28" height="28">
    <path d="M12 2L2 7v10l10 5 10-5V7L12 2zm0 2.5L19 8l-7 3.5L5 8l7-3.5zM4 9.5l7 3.5v7l-7-3.5v-7zm9 10.5v-7l7-3.5v7l-7 3.5z"/>
  </svg>
);

const SendIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
    <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
  </svg>
);

const SettingsIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
    <path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
  </svg>
);

const BrainIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
    <path d="M12 2a9 9 0 0 0-9 9c0 4.17 2.84 7.67 6.69 8.69L12 22l2.31-2.31C18.16 18.67 21 15.17 21 11a9 9 0 0 0-9-9zm0 16c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z"/>
    <circle cx="12" cy="11" r="3"/>
  </svg>
);

const TrashIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
    <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
  </svg>
);

const CloseIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
  </svg>
);

const KeyIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
    <path d="M12.65 10C11.83 7.67 9.61 6 7 6c-3.31 0-6 2.69-6 6s2.69 6 6 6c2.61 0 4.83-1.67 5.65-4H17v4h4v-4h2v-4H12.65zM7 14c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/>
  </svg>
);

const SparkleIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
    <path d="M12 2L9.5 9.5 2 12l7.5 2.5L12 22l2.5-7.5L22 12l-7.5-2.5z"/>
  </svg>
);

const NewChatIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
    <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
  </svg>
);

const HistoryIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
    <path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/>
  </svg>
);

const ClearMemoryIcon = () => (
  <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm5 11H7v-2h10v2z"/>
  </svg>
);

const EXAMPLE_QUESTIONS = [
  { icon: '📊', title: 'Risk Analysis', question: 'Analyze the credit risk for customer 93486' },
  { icon: '🔍', title: 'Customer Lookup', question: 'What are the details for customer 34997?' },
  { icon: '📈', title: 'Risk Factors', question: 'What factors indicate high credit risk?' },
  { icon: '💡', title: 'Recommendations', question: 'Give me recommendations for managing high-risk customers' },
];

function App() {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [threadId, setThreadId] = useState(() => generateThreadId());
  const [showSettings, setShowSettings] = useState(false);
  const [showMemory, setShowMemory] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [historyThreads, setHistoryThreads] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [tokenInput, setTokenInput] = useState('');
  const [userIdInput, setUserIdInput] = useState('');
  const [tokenExists, setTokenExists] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    const existingToken = getToken();
    setTokenExists(hasToken());
    if (existingToken) {
      setTokenInput(existingToken);
    }
    const existingUserId = getUserId();
    if (existingUserId && existingUserId !== 'default_user') {
      setUserIdInput(existingUserId);
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const content = inputValue.trim();
    if (!content || isLoading) return;

    const userMessage = {
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      const conversationHistory = [...messages, userMessage].map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      const response = await callAgent(conversationHistory, threadId);

      const assistantMessage = {
        role: 'assistant',
        content: response.content,
        timestamp: new Date().toISOString(),
        memoryEnabled: response.memoryEnabled
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Agent call failed:', error);
      const errorMessage = {
        role: 'assistant',
        content: `**Error:** ${error.message}\n\nPlease click the ⚙️ Settings button to configure your Databricks token.`,
        timestamp: new Date().toISOString(),
        isError: true
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleExampleClick = (question) => {
    setInputValue(question);
    inputRef.current?.focus();
  };

  const clearChat = () => {
    setMessages([]);
    setThreadId(generateThreadId());
  };

  const startNewThread = () => {
    setMessages([]);
    setThreadId(generateThreadId());
  };

  const handleSaveSettings = () => {
    if (tokenInput.trim()) {
      saveToken(tokenInput.trim());
      setTokenExists(true);
    }
    if (userIdInput.trim()) {
      saveUserId(userIdInput.trim());
    }
    setShowSettings(false);
    console.log('[App] Settings saved');
  };

  const handleClearToken = () => {
    clearToken();
    setTokenInput('');
    setTokenExists(false);
  };

  const handleLoadHistory = async () => {
    setHistoryLoading(true);
    try {
      const data = await getUserThreads();
      setHistoryThreads(data.threads || []);
      setShowHistory(true);
    } catch (error) {
      console.error('Failed to load history:', error);
      alert('Failed to load conversation history');
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleLoadThread = async (thread) => {
    try {
      const data = await getThreadHistory(thread.thread_id);
      if (data.messages && data.messages.length > 0) {
        const loadedMessages = data.messages.map(m => ({
          role: m.role,
          content: m.content,
          timestamp: m.created_at
        }));
        setMessages(loadedMessages);
        setThreadId(thread.thread_id);
        setShowHistory(false);
      }
    } catch (error) {
      console.error('Failed to load thread:', error);
      alert('Failed to load conversation');
    }
  };

  const handleClearMemory = async () => {
    try {
      await clearUserMemories();
      setShowClearConfirm(false);
      alert('Memory cleared! The agent will no longer remember previous analysis.');
    } catch (error) {
      console.error('Failed to clear memory:', error);
      alert('Failed to clear memory: ' + error.message);
    }
  };

  return (
    <div className="app">
      {/* Settings Modal */}
      {showSettings && (
        <div className="modal-overlay" onClick={() => setShowSettings(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">
                <KeyIcon />
                <h3>Settings</h3>
              </div>
              <button className="modal-close" onClick={() => setShowSettings(false)}>
                <CloseIcon />
              </button>
            </div>

            <div className="modal-body">
              <div className="setting-group">
                <label htmlFor="token-input">Databricks Token</label>
                <input
                  id="token-input"
                  type="password"
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  placeholder="dapi..."
                  className="setting-input"
                />
                <span className="setting-hint">Personal Access Token for authentication</span>
              </div>

              <div className="setting-group">
                <label htmlFor="userid-input">User ID (for Memory)</label>
                <input
                  id="userid-input"
                  type="text"
                  value={userIdInput}
                  onChange={(e) => setUserIdInput(e.target.value)}
                  placeholder="your.email@example.com"
                  className="setting-input"
                />
                <span className="setting-hint">Used to personalize and remember your preferences</span>
              </div>

              {tokenExists && (
                <div className="token-status success">
                  <span>✓ Token configured</span>
                </div>
              )}
            </div>

            <div className="modal-footer">
              {tokenExists && (
                <button className="btn-secondary" onClick={handleClearToken}>
                  Clear Token
                </button>
              )}
              <button className="btn-primary" onClick={handleSaveSettings}>
                Save Settings
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Memory Panel */}
      <MemoryPanel isOpen={showMemory} onClose={() => setShowMemory(false)} />

      {/* History Panel Modal */}
      {showHistory && (
        <div className="modal-overlay" onClick={() => setShowHistory(false)}>
          <div className="modal history-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">
                <HistoryIcon />
                <h3>Conversation History</h3>
              </div>
              <button className="modal-close" onClick={() => setShowHistory(false)}>
                <CloseIcon />
              </button>
            </div>
            <div className="modal-body">
              {historyLoading ? (
                <div className="loading-state">Loading conversations...</div>
              ) : historyThreads.length === 0 ? (
                <div className="empty-state">No previous conversations found.</div>
              ) : (
                <div className="thread-list">
                  {historyThreads.map((thread, index) => (
                    <div 
                      key={index} 
                      className={`thread-item ${thread.thread_id === threadId ? 'active' : ''}`}
                      onClick={() => handleLoadThread(thread)}
                    >
                      <div className="thread-preview">{thread.first_message}</div>
                      <div className="thread-meta">
                        <span>{thread.message_count} messages</span>
                        <span>{new Date(thread.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Clear Memory Confirmation Modal */}
      {showClearConfirm && (
        <div className="modal-overlay" onClick={() => setShowClearConfirm(false)}>
          <div className="modal confirm-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div className="modal-title">
                <ClearMemoryIcon />
                <h3>Clear Memory?</h3>
              </div>
              <button className="modal-close" onClick={() => setShowClearConfirm(false)}>
                <CloseIcon />
              </button>
            </div>
            <div className="modal-body">
              <p>This will delete all remembered information:</p>
              <ul className="clear-list">
                <li>• Customer emails</li>
                <li>• Risk assessments</li>
                <li>• Customer names & financial data</li>
                <li>• Analysis history</li>
              </ul>
              <p className="clear-note">💾 Chat history will be preserved for audit.</p>
            </div>
            <div className="modal-footer">
              <button className="btn-secondary" onClick={() => setShowClearConfirm(false)}>
                Cancel
              </button>
              <button className="btn-danger" onClick={handleClearMemory}>
                Clear Memory
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="header-left">
            <div className="logo">
              <DatabricksIcon />
            </div>
            <div className="header-text">
              <h1>Credit Risk Analyst Agent <span className="memory-tag">with Memory</span></h1>
              <p>Powered by Agentbricks & Lakebase</p>
            </div>
          </div>
          <div className="header-right">
            <div className="thread-info">
              <span className="thread-label">Thread:</span>
              <code>{threadId.slice(-12)}</code>
            </div>
            <button
              className="header-btn memory-btn"
              onClick={() => setShowMemory(true)}
              title="View Memory"
            >
              <BrainIcon />
              <span>Memory</span>
            </button>
            <button
              className="header-btn history-btn"
              onClick={handleLoadHistory}
              title="View History"
              disabled={historyLoading}
            >
              <HistoryIcon />
              <span>History</span>
            </button>
            <button
              className="header-btn clear-memory-btn"
              onClick={() => setShowClearConfirm(true)}
              title="Clear Memory"
            >
              <ClearMemoryIcon />
            </button>
            <button
              className="header-btn"
              onClick={() => setShowSettings(true)}
              title="Settings"
            >
              <SettingsIcon />
            </button>
            <button
              className="header-btn new-chat-btn"
              onClick={startNewThread}
              title="New Thread"
            >
              <NewChatIcon />
              <span>New</span>
            </button>
            {messages.length > 0 && (
              <button className="header-btn clear-btn" onClick={clearChat} title="Clear chat">
                <TrashIcon />
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main">
        {!tokenExists && (
          <div className="token-banner">
            <KeyIcon />
            <span>Configure your <strong>Databricks Token</strong> and <strong>User ID</strong> in Settings to enable memory features</span>
            <button onClick={() => setShowSettings(true)}>Configure</button>
          </div>
        )}

        {messages.length === 0 ? (
          <div className="welcome">
            <div className="welcome-header">
              <div className="welcome-icon">
                <SparkleIcon />
              </div>
              <h2>Credit Risk Analyst Agent with Memory</h2>
              <p>
                I remember our conversations and learn your preferences over time.
                Ask me about credit risk analysis, and I'll provide personalized insights.
              </p>
            </div>

            <div className="memory-features">
              <div className="feature-card">
                <div className="feature-icon">🧠</div>
                <h4>Long-term Memory</h4>
                <p>I remember key insights from previous conversations</p>
              </div>
              <div className="feature-card">
                <div className="feature-icon">💬</div>
                <h4>Session Context</h4>
                <p>I maintain context within each conversation thread</p>
              </div>
              <div className="feature-card">
                <div className="feature-icon">👤</div>
                <h4>Personalization</h4>
                <p>I learn your preferences and analysis patterns</p>
              </div>
            </div>

            <div className="example-grid">
              {EXAMPLE_QUESTIONS.map((item, index) => (
                <button
                  key={index}
                  className="example-card"
                  onClick={() => handleExampleClick(item.question)}
                >
                  <div className="example-icon">{item.icon}</div>
                  <div className="example-content">
                    <span className="example-title">{item.title}</span>
                    <span className="example-text">{item.question}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="chat-container">
            <div className="messages">
              {messages.map((message, index) => (
                <ChatMessage
                  key={index}
                  message={message}
                  showMemoryBadge={message.memoryEnabled}
                />
              ))}
              {isLoading && (
                <div className="loading-message">
                  <div className="loading-avatar">
                    <DatabricksIcon />
                  </div>
                  <div className="loading-content">
                    <div className="loading-dots">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                    <span className="loading-text">Analyzing with memory...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>
        )}
      </main>

      {/* Input Footer */}
      <footer className="footer">
        <form className="input-form" onSubmit={handleSubmit}>
          <div className="input-wrapper">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Ask about credit risk analysis..."
              disabled={isLoading}
              className="chat-input"
            />
            <button
              type="submit"
              className="send-btn"
              disabled={!inputValue.trim() || isLoading}
            >
              {isLoading ? (
                <div className="spinner"></div>
              ) : (
                <SendIcon />
              )}
            </button>
          </div>
          <div className="input-hint">
            Press Enter to send • Memory: <span className={hasUserId() ? 'active' : 'inactive'}>{hasUserId() ? getUserId() : 'Not configured'}</span>
          </div>
        </form>
      </footer>
    </div>
  );
}

export default App;
