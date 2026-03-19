# Credit Risk Analyst Agent with Memory - Setup Guide

This guide explains how to deploy the Credit Risk Analyst Agent app with your own Databricks serving endpoint and Lakebase instance.

---

## Prerequisites

1. **Databricks Workspace** with:
   - Model Serving endpoint (Agent deployed)
   - Lakebase instance created
   - Databricks App enabled

2. **Lakebase Tables** - Create these tables in your Lakebase instance:

```sql
-- Run this SQL in a notebook connected to your Lakebase instance

CREATE TABLE IF NOT EXISTS app_conversation_history (
    id SERIAL PRIMARY KEY,
    thread_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_user_memories (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(100) NOT NULL,
    memory_key VARCHAR(255) NOT NULL,
    memory_value TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, memory_type, memory_key)
);

CREATE TABLE IF NOT EXISTS app_conversation_summaries (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    thread_id VARCHAR(255) NOT NULL UNIQUE,
    summary TEXT NOT NULL,
    customer_ids TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Grant permissions to app's service principal (get ID from app settings)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO "<service-principal-id>";
```

---

## Configuration - Files to Update

### 1. `app.yaml` (3 values to change)

```yaml
env:
  - name: DATABRICKS_HOST
    value: "<YOUR_WORKSPACE_URL>"          # e.g., https://adb-123456789.11.azuredatabricks.net
  - name: SERVING_ENDPOINT
    value: "<YOUR_AGENT_ENDPOINT>"         # e.g., my-credit-agent-endpoint
  - name: LAKEBASE_INSTANCE_NAME
    value: "<YOUR_LAKEBASE_INSTANCE>"      # e.g., my-lakebase-instance

resources:
  serving_endpoints:
    - name: <YOUR_AGENT_ENDPOINT>          # Same as SERVING_ENDPOINT above
      permission: CAN_QUERY
```

### 2. `src/services/agentService.js` (1 value to change)

```javascript
const AGENT_ENDPOINT = '/api/serving-endpoints/<YOUR_AGENT_ENDPOINT>/invocations';
```

Then rebuild the frontend:
```bash
npm install
npm run build
```

---

## Quick Setup Checklist

| Step | File | What to Change |
|------|------|----------------|
| 1 | `app.yaml` | `DATABRICKS_HOST` → Your workspace URL |
| 2 | `app.yaml` | `SERVING_ENDPOINT` → Your agent endpoint name |
| 3 | `app.yaml` | `LAKEBASE_INSTANCE_NAME` → Your Lakebase instance name |
| 4 | `app.yaml` | `serving_endpoints.name` → Same as step 2 |
| 5 | `src/services/agentService.js` | `AGENT_ENDPOINT` → Your agent endpoint name |
| 6 | Terminal | Run `npm run build` to rebuild frontend |
| 7 | Lakebase | Create tables (SQL above) |
| 8 | Lakebase | Grant permissions to app's service principal |

---

## Deployment Steps

1. **Update Configuration** (steps 1-6 above)

2. **Upload to Databricks Workspace**
   ```bash
   databricks workspace import-dir ./deploy "/Workspace/Users/<your-email>/credit-memory-app" --overwrite
   ```

3. **Create Databricks App**
   - Go to Compute → Apps → Create App
   - Point to the workspace folder
   - App will use `app.yaml` for configuration

4. **Create Lakebase Tables**
   - Run the SQL from Prerequisites section
   - Grant permissions to the app's service principal

5. **Start the App**
   - Deploy and start from Databricks Apps UI

---

## Troubleshooting

### "No module named 'psycopg2'"
- Check `requirements.txt` has `psycopg2-binary>=2.9.0`

### "relation does not exist"
- Create the Lakebase tables (see Prerequisites)

### "permission denied for schema public"
- Grant CREATE/INSERT permissions to the app's service principal

### "404 on serving endpoint"
- Verify endpoint name matches in `app.yaml` AND `agentService.js`
- Rebuild frontend after changing `agentService.js`

### "Lakebase connection failed"
- Verify `LAKEBASE_INSTANCE_NAME` is correct
- Check the instance exists and is running

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend (React)                                            │
│  - agentService.js calls /api/serving-endpoints/...         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Backend (Flask - app.py)                                    │
│  - Proxies to Model Serving endpoint                        │
│  - Manages memory in Lakebase                               │
│  - Config from environment variables (app.yaml)             │
└─────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┴───────────────┐
          ▼                               ▼
┌──────────────────────┐    ┌──────────────────────────────┐
│  Model Serving       │    │  Lakebase (PostgreSQL)       │
│  (Agent Endpoint)    │    │  - app_conversation_history  │
│                      │    │  - app_user_memories         │
│                      │    │  - app_conversation_summaries│
└──────────────────────┘    └──────────────────────────────┘
```
