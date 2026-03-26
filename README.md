# Credit Risk Analyst Agent with Lakebase Memory

A Credit Risk Analyst AI Agent built with Databricks Agentbricks that features **persistent memory** powered by Databricks Lakebase. The agent remembers customer analyses, risk assessments, and conversation history across sessions.

This is extended version of Databricks Solution: https://www.databricks.com/resources/demos/tutorials/lakehouse-platform/lakehouse-credit-decisioning
I have added this new module to implement agent memory with Lakebase.

---

## Business Problem

Financial institutions face critical challenges in credit risk assessment:

| Challenge | Impact |
|-----------|--------|
| **Manual Analysis Bottleneck** | Credit analysts spend 60-70% of time gathering data from disparate systems |
| **Inconsistent Risk Decisions** | Different analysts apply varying criteria, leading to compliance risks |
| **No Institutional Memory** | Each analysis starts from scratch; past insights on customers are lost |
| **Audit Trail Gaps** | Difficulty demonstrating regulatory compliance without complete conversation history |
| **Slow Time-to-Decision** | Loan approvals delayed due to manual data aggregation |

**This solution addresses these problems by:**
- Automating data retrieval from multiple sources (credit bureaus, financial statements, transaction history)
- Applying consistent risk scoring through AI-powered analysis
- Maintaining persistent memory of all customer interactions and assessments
- Providing complete audit trails for regulatory compliance (FCRA, ECOA, Basel III)
- Reducing credit decision time from days to minutes

---

## Why Databricks for Production-Grade AI Agents

Databricks provides a unified platform to build, deploy, and scale enterprise AI agents:

### 1. **Agentbricks Framework**
- Build sophisticated multi-tool agents with Unity Catalog function integration
- Native support for LangGraph conversation flows
- Seamless integration with Databricks Model Serving

### 2. **Lakebase (Managed PostgreSQL)**
- Fully-managed database for persistent agent memory
- No infrastructure management; automatic scaling and backups
- SQL-compatible for easy querying and compliance reporting
- Built-in authentication via Databricks service principals

### 3. **Model Serving Endpoints**
- Deploy agents as scalable REST APIs with one click
- Built-in authentication and rate limiting
- Auto-scaling based on demand; pay only for what you use
- Supports Foundation Models (GPT-4, Claude, Llama) or custom fine-tuned models

### 4. **Databricks Apps**
- Deploy frontend applications within your Databricks workspace
- Single Sign-On (SSO) with existing enterprise identity
- No separate hosting infrastructure required
- Secure access to data and models without credential management

### 5. **Unity Catalog Integration**
- Govern AI functions and tools centrally
- Row-level security on customer data
- Audit logging for all data access
- Share tools across teams with fine-grained permissions

### 6. **Enterprise Security & Compliance**
- Data never leaves your cloud environment
- SOC 2 Type II, HIPAA, FedRAMP certified
- Complete lineage tracking for model decisions
- Role-based access control (RBAC) at every layer

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DATABRICKS AGENTIC ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│   │ Databricks   │    │   Model      │    │    Unity Catalog         │  │
│   │    Apps      │───▶│  Serving     │───▶│  (Functions & Data)      │  │
│   │  (React UI)  │    │ (Agent API)  │    │                          │  │
│   └──────────────┘    └──────────────┘    └──────────────────────────┘  │
│          │                   │                        │                  │
│          │                   ▼                        │                  │
│          │         ┌──────────────────┐              │                  │
│          │         │    Lakebase      │              │                  │
│          └────────▶│ (Agent Memory)   │◀─────────────┘                  │
│                    └──────────────────┘                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisite: 

Build Databricks agent with  [Agentbricks Supervisor Agent](https://docs.databricks.com/aws/en/generative-ai/agent-bricks/)  or build a [custom agent](https://docs.databricks.com/aws/en/generative-ai/agent-framework/author-agent), get the Agent endpoint once it is ready. 

Replace the agent in app code with your agent end point. ( Refer : deploy-template )


---


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

### Credit Risk Agent Chat Interface

![Credit Risk Agent UI](images/credit-risk-agent-ui.png)

*The agent chat interface showing memory-enabled conversations with persistent context across sessions.*

## Lakebase Memory Tables

| Table | Purpose |
|-------|---------|
| `app_conversation_history` | Full message history (thread_id, user_id, role, content) |
| `app_user_memories` | Long-term memories (memory_type, memory_key, memory_value) |
| `app_conversation_summaries` | Thread summaries with customer IDs discussed |

## Project Structure

```
credit-risk-analyst/
├── setup/                                  # *** One-command data installation ***
│   ├── 00_install.sh                       # Main installer — runs everything end-to-end
│   ├── config.py                           # Central config (catalog, schema, table names, models)
│   ├── 01_create_catalog.py                # Create Unity Catalog, schema, volume
│   ├── 02_generate_data.py                 # Generate 1000 Indian banking synthetic records
│   ├── 03_create_functions.py              # Create UC functions (get_customer_details, credit_report_generator)
│   ├── 04_load_rag_chunks.py               # Load markdown knowledge docs into Delta table
│   ├── 05_create_vector_search.py          # Create Vector Search endpoint + index
│   ├── 06_create_lakebase.py               # Create Lakebase instance + memory tables
│   └── knowledge_docs/                     # RAG knowledge base (markdown)
│       ├── 01_credit_decision_logic_playbook.md
│       ├── 02_product_routing_rules.md
│       └── 03_rbi_compliance_checklist.md
├── app.py                                  # Flask backend with memory layer
├── app.yaml                                # Databricks App config
├── requirements.txt                        # Python dependencies
├── deploy/                                 # Production deployment files
│   ├── app.py                              # Production Flask app
│   ├── app.yaml                            # Databricks App config
│   ├── requirements.txt                    # Python dependencies
│   └── dist/                               # Built React frontend
├── deploy-template/                        # Template for new deployments
│   ├── app.py                              # Template app with agent endpoint placeholder
│   ├── app.yaml                            # Template Databricks App config
│   ├── SETUP_GUIDE.md                      # Step-by-step deployment guide
│   └── src/                                # React source template
├── src/                                    # React frontend source
│   ├── App.jsx                             # Main chat interface
│   ├── components/                         # UI components (ChatMessage, MemoryPanel)
│   └── services/                           # Agent API service layer
├── sample_data/                            # Generated sample data (after running installer)
│   ├── underbanked_prediction.csv          # 1000 customer financial profiles
│   └── cust_personal_info.csv              # 100 customer personal details
├── dist/                                   # Built frontend assets
├── images/                                 # Screenshots and diagrams
├── index.html                              # Frontend entry point
├── package.json                            # Node.js dependencies
├── vite.config.js                          # Vite build config
└── ENDPOINT_CONFIG.md                      # Agent endpoint configuration guide
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

- Databricks Workspace with a SQL warehouse
- Databricks CLI installed and authenticated (`pip install databricks-cli`)
- Python 3.8+ with `numpy`

### Step 1: Install All Databricks Assets (One Command)

```bash
# Using default config (catalog: fsi_credit_agent)
./setup/00_install.sh <databricks-profile>

# Or override catalog via env var (for workspaces where you can't create catalogs)
UC_CATALOG="your_catalog" ./setup/00_install.sh <databricks-profile>
```

This creates: catalog, schema, volume, 2 tables (1000 + 100 rows), 2 UC functions, RAG chunks table, Vector Search endpoint + index, Genie space, and Lakebase instance.

### Step 2: Build the Frontend

```bash
npm install
npm run build
```

### Step 3: Run Locally

```bash
pip install -r requirements.txt
python app.py
```

### Step 4: Deploy to Databricks

1. Copy `deploy/` folder to Databricks workspace
2. Create a Databricks App pointing to `deploy/app.py`
3. Configure the app with required permissions for Lakebase and Model Serving

### Configuration

Edit `setup/config.py` to customize:

| Setting | Default | Description |
|---------|---------|-------------|
| `CATALOG` | `fsi_credit_agent` | Unity Catalog name |
| `SCHEMA` | `agent_schema` | Schema name |
| `AGENT_MODEL` | `databricks-gpt-oss-120b` | LLM for credit report generation |
| `NUM_CUSTOMERS_FULL` | `1000` | Number of synthetic customer records |

All settings can also be overridden via environment variables (`UC_CATALOG`, `UC_SCHEMA`, etc.).

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
