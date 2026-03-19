# Credit Risk Analyst Agent with Memory - Deployment Template

Reusable Databricks App template for deploying the Credit Risk Analyst Agent with persistent memory.

## Quick Start

### Step 1: Update Configuration (5 values total)

**File: `app.yaml`** - Update 4 values:
```yaml
- name: DATABRICKS_HOST
  value: "<YOUR_WORKSPACE_URL>"       # Your Databricks workspace URL

- name: SERVING_ENDPOINT  
  value: "<YOUR_ENDPOINT_NAME>"       # Your agent serving endpoint

- name: LAKEBASE_INSTANCE_NAME
  value: "<YOUR_LAKEBASE_NAME>"       # Your Lakebase instance name

serving_endpoints:
  - name: <YOUR_ENDPOINT_NAME>        # Same as SERVING_ENDPOINT
```

**File: `src/services/agentService.js`** - Update 1 value:
```javascript
const AGENT_ENDPOINT = '/api/serving-endpoints/<YOUR_ENDPOINT_NAME>/invocations';
```

### Step 2: Build Frontend
```bash
npm install
npm run build
```

### Step 3: Create Lakebase Tables

Run this SQL in a notebook connected to your Lakebase:

```sql
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
```

### Step 4: Deploy to Databricks

```bash
# Upload to workspace
databricks workspace import-dir . "/Workspace/Users/<your-email>/credit-memory-app" --overwrite

# Or use Databricks CLI sync
databricks sync . "/Workspace/Users/<your-email>/credit-memory-app"
```

### Step 5: Create & Start App

1. Go to **Compute → Apps → Create App**
2. Point to the workspace folder
3. Grant permissions to the app's service principal for Lakebase
4. Start the app

---

## Configuration Summary

| File | Variable | Description |
|------|----------|-------------|
| `app.yaml` | `DATABRICKS_HOST` | Your workspace URL |
| `app.yaml` | `SERVING_ENDPOINT` | Agent endpoint name |
| `app.yaml` | `LAKEBASE_INSTANCE_NAME` | Lakebase instance name |
| `app.yaml` | `serving_endpoints.name` | Same as SERVING_ENDPOINT |
| `agentService.js` | `AGENT_ENDPOINT` | Same endpoint in URL path |

---

## File Structure

```
deploy-template/
├── README.md              # This file
├── SETUP_GUIDE.md         # Detailed setup instructions
├── app.py                 # Flask backend (reads config from env)
├── app.yaml               # Databricks App config (UPDATE THIS)
├── requirements.txt       # Python dependencies
├── package.json           # Node.js dependencies
├── vite.config.js         # Vite build config
├── index.html             # Frontend entry
├── src/                   # React frontend source
│   ├── App.jsx
│   ├── App.css
│   ├── components/
│   └── services/
│       └── agentService.js  # (UPDATE ENDPOINT HERE)
└── dist/                  # Built frontend (after npm run build)
```

---

## Troubleshooting

See `SETUP_GUIDE.md` for detailed troubleshooting.

**Common Issues:**
- 404 on endpoint → Check endpoint name matches in both `app.yaml` AND `agentService.js`
- Tables don't exist → Run the CREATE TABLE SQL in Lakebase
- Permission denied → Grant permissions to app's service principal
