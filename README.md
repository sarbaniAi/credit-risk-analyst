# Credit Risk Analyst Agent with Lakebase Memory

A Credit Risk Analyst AI Agent built with Databricks Agentbricks that features **persistent memory** powered by Databricks Lakebase. The agent remembers customer analyses, risk assessments, and conversation history across sessions.

This is extended Agnet version of Databricks Solution :https://www.databricks.com/resources/demos/tutorials/lakehouse-platform/lakehouse-credit-decisioning
I have added this new module to implement agent memory with Lakebase.

## Features

- **Persistent Long-Term Memory** - Stores customer insights, risk assessments, and emails across sessions using Lakebase (Databricks' managed PostgreSQL)
- **Conversation History** - Full audit trail of all interactions for compliance
- **Credit Risk Analysis** - Analyzes customer financial data and generates risk assessments
- **Memory Recall** - Ask "What customers have I analyzed?" and the agent remembers
- **Per-User Isolation** - Each user has their own memory space
- **Deployed as Databricks App** - Runs within Databricks with built-in SSO

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Databricks App (React UI)                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Flask Backend (app.py)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Memory    │  │   Memory    │  │      Agent Proxy        │  │
│  │  Injection  │  │ Extraction  │  │  (Model Serving)        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Databricks Lakebase                           │
│  ┌───────────────────┐ ┌───────────────┐ ┌──────────────────┐   │
│  │ app_conversation_ │ │ app_user_     │ │ app_conversation_│   │
│  │     history       │ │   memories    │ │    summaries     │   │
│  └───────────────────┘ └───────────────┘ └──────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Lakebase Memory Tables

| Table | Purpose |
|-------|---------|
| `app_conversation_history` | Full message history (thread_id, user_id, role, content) |
| `app_user_memories` | Long-term memories (memory_type, memory_key, memory_value) |
| `app_conversation_summaries` | Thread summaries with customer IDs discussed |

## Project Structure

```
08-DB-Memory-App/
├── agent_with_memory.py    # Credit Risk Agent with LangGraph & memory
├── app.py                  # Flask backend with memory layer
├── driver.py               # Agent driver for local testing
├── deploy/                 # Production deployment files
│   ├── app.py              # Production Flask app
│   ├── app.yaml            # Databricks App config
│   ├── requirements.txt    # Python dependencies
│   └── dist/               # Built React frontend
├── src/                    # React frontend source
│   ├── App.jsx             # Main chat interface
│   ├── components/
│   │   ├── ChatMessage.jsx # Chat message component
│   │   └── MemoryPanel.jsx # Memory viewer panel
│   └── services/
│       └── agentService.js # Agent API service
├── index.html              # Frontend entry point
├── package.json            # Node.js dependencies
├── vite.config.js          # Vite build config
└── VIDEO_SCRIPT.md         # Demo script
```

## Technologies Used

- **Databricks Agentbricks** - AI agent framework
- **Databricks Lakebase** - Managed PostgreSQL for memory storage
- **Databricks Apps** - Deployment platform with SSO
- **LangGraph** - Conversation state management
- **React + Vite** - Frontend framework
- **Flask** - Backend API server

## Getting Started

### Prerequisites

- Databricks Workspace with Lakebase enabled
- Model Serving endpoint with LLM access
- Unity Catalog functions for credit risk tools

### Local Development

1. Install dependencies:
```bash
npm install
pip install -r requirements.txt
```

2. Build the frontend:
```bash
npm run build
```

3. Run locally:
```bash
python app.py
```

### Deploy to Databricks

1. Copy `deploy/` folder to Databricks workspace
2. Create a Databricks App pointing to `deploy/app.py`
3. Configure the app with required permissions for Lakebase and Model Serving

## Usage Examples

```
# Analyze a customer
"Analyze customer 34997"

# Memory recall (in new conversation)
"What customers have I analyzed?"
"What's the email for my customer?"

# Get risk assessment
"What risk factors contributed to this assessment?"
```

## Memory Flow

1. **User sends message** → Stored in `app_conversation_history`
2. **Memory injection** → Previous memories retrieved and injected as silent context
3. **Agent responds** → Response analyzed for customer IDs, emails, risk levels
4. **Memory extraction** → Key insights stored in `app_user_memories`
5. **Next session** → Agent recalls all stored memories

## License

Internal use - Databricks

## Author

Sarbani Maiti - Databricks
