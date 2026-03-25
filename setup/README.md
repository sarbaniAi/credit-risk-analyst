# Setup Guide — Credit Risk Analyst Agent

Automated setup scripts to deploy the Credit Risk Analyst Agent demo on **any** Databricks workspace (AWS or Azure).

## Prerequisites

- Databricks CLI installed and authenticated (`pip install databricks-cli`)
- A Databricks workspace with Unity Catalog enabled
- A running SQL warehouse
- Python 3.9+ (for local script execution)

## Quick Start (One Command)

```bash
# Authenticate with your workspace
databricks auth login https://<your-workspace>.databricks.net --profile=my-workspace

# Run the installer
./setup/00_install.sh my-workspace
```

## Step-by-Step Setup

If you prefer to run each step manually:

### Step 1: Create Catalog & Schema

Run `01_create_catalog.py` as a Databricks notebook.

Creates:
- Catalog: `fsi_credit_agent`
- Schema: `fsi_credit_agent.agent_schema`
- Volume: `fsi_credit_agent.agent_schema.credit_docs`

### Step 2: Generate Sample Data

Run `02_generate_data.py` as a Databricks notebook.

Creates **1,000 Indian banking customer records** with:
- Indian names (Aarav Sharma, Priya Patel, etc.)
- INR income ranges (1.5L - 50L+)
- UPI/NEFT transaction patterns
- CIBIL-style risk predictions
- Payment delay history
- Overdraft and deposit patterns

**Tables created:**
| Table | Rows | Description |
|-------|------|-------------|
| `underbanked_prediction` | 1,000 | Full financial + transaction + risk data (61 columns) |
| `cust_personal_info` | 100 | Customer name, email, phone, risk prediction |

### Step 3: Create UC Functions

Run `03_create_functions.py` as a Databricks notebook.

Creates:
- `get_customer_details(customer_id)` — Retrieves customer financial data by ID
- `credit_report_generator(...)` — Uses AI to generate credit risk reports with RBI/CIBIL context

### Step 4: Load Knowledge Base

Run `04_load_rag_chunks.py` as a Databricks notebook.

Loads 3 markdown knowledge documents into the `rag_chunks` Delta table:
- `01_credit_decision_logic_playbook.md` — Segmentation, scoring, decision matrix
- `02_product_routing_rules.md` — Product eligibility, bundles, loan limits
- `03_rbi_compliance_checklist.md` — IRAC norms, Fair Practices Code, PSL targets

### Step 5: Create Vector Search Index

Run `05_create_vector_search.py` as a Databricks notebook.

Creates:
- Vector Search endpoint: `credit-risk-vs-endpoint`
- Vector Search index with managed embeddings (`databricks-gte-large-en`) from `rag_chunks`

### Step 6: Create Lakebase Instance

Run locally or as notebook:
```bash
python setup/06_create_lakebase.py --profile=my-workspace
```

Creates:
- Lakebase instance: `credit-risk-lakebase`
- Memory tables: `app_conversation_history`, `app_user_memories`, `app_conversation_summaries`

### Step 7: Create Agent & Deploy App

Use the Databricks AI Dev Kit / AgentBricks to create the Supervisor agent pointing to:

| Component | Value |
|-----------|-------|
| **Tables** | `fsi_credit_agent.agent_schema.underbanked_prediction`, `fsi_credit_agent.agent_schema.cust_personal_info` |
| **UC Functions** | `fsi_credit_agent.agent_schema.get_customer_details`, `fsi_credit_agent.agent_schema.credit_report_generator` |
| **Vector Search** | Endpoint: `credit-risk-vs-endpoint`, Index: `fsi_credit_agent.agent_schema.credit_policy_index` |
| **Genie Space** | Create from the two tables above |
| **Lakebase** | Instance: `credit-risk-lakebase` |
| **Model** | `databricks-GPT-OSS-120B` (or your preferred model) |

## Configuration

All settings are centralized in `setup/config.py`. Modify before running:

```python
CATALOG = "fsi_credit_agent"       # Change if needed
SCHEMA = "agent_schema"            # Change if needed
NUM_CUSTOMERS_FULL = 1000          # Number of customers to generate
AGENT_MODEL = "databricks-GPT-OSS-120B"  # LLM model for the agent
```

## File Structure

```
setup/
├── config.py                  # Central configuration
├── 00_install.sh              # One-command installer
├── 01_create_catalog.py       # Create UC catalog, schema, volume
├── 02_generate_data.py        # Generate Indian banking synthetic data
├── 03_create_functions.py     # Create UC functions for the agent
├── 04_load_rag_chunks.py      # Load knowledge docs into rag_chunks table
├── 05_create_vector_search.py # Create VS endpoint + index from rag_chunks
├── 06_create_lakebase.py      # Create Lakebase instance + memory tables
├── knowledge_docs/            # Credit policy knowledge base (markdown)
│   ├── 01_credit_decision_logic_playbook.md
│   ├── 02_product_routing_rules.md
│   └── 03_rbi_compliance_checklist.md
└── README.md                  # This file
```
