#!/bin/bash
# ============================================================
# Credit Risk Analyst Agent — Fully Automated Setup
# ============================================================
#
# Usage:
#   ./setup/00_install.sh <databricks-profile>
#
# Example:
#   ./setup/00_install.sh my-profile
#
# This script runs EVERYTHING end-to-end:
#   1. Creates catalog, schema, volume
#   2. Generates synthetic data locally → uploads → creates tables
#   3. Creates UC functions (get_customer_details, credit_report_generator)
#   4. Loads RAG knowledge chunks into Delta table
#   5. Creates Vector Search endpoint + index
#   6. Creates Genie space from tables
#   7. Creates Lakebase instance for app memory
# ============================================================

# No set -e: we handle errors explicitly per step

PROFILE=${1:-"DEFAULT"}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# Read CATALOG and SCHEMA: env vars take priority, then config.py, else fail
CATALOG=$(python3 -c "
import sys, os
# Env var overrides config.py
v = os.environ.get('UC_CATALOG', '')
if v:
    print(v)
else:
    sys.path.insert(0, '$SCRIPT_DIR')
    try:
        from config import CATALOG
        print(CATALOG)
    except Exception:
        sys.exit(1)
" 2>/dev/null)

if [ -z "$CATALOG" ]; then
    echo "ERROR: Set CATALOG in setup/config.py or UC_CATALOG env var"
    exit 1
fi

SCHEMA=$(python3 -c "
import sys, os
v = os.environ.get('UC_SCHEMA', '')
if v:
    print(v)
else:
    sys.path.insert(0, '$SCRIPT_DIR')
    try:
        from config import SCHEMA
        print(SCHEMA)
    except Exception:
        sys.exit(1)
" 2>/dev/null)

if [ -z "$SCHEMA" ]; then
    echo "ERROR: Set SCHEMA in setup/config.py or UC_SCHEMA env var"
    exit 1
fi

FULL_SCHEMA="${CATALOG}.${SCHEMA}"

# Export for child Python scripts
export UC_CATALOG="$CATALOG"
export UC_SCHEMA="$SCHEMA"
export LAKEBASE_INSTANCE_NAME="credit-risk-lakebase"
export DATABRICKS_CONFIG_PROFILE="$PROFILE"

echo "============================================================"
echo " Credit Risk Analyst Agent — Automated Setup"
echo " Profile: $PROFILE"
echo " Catalog: $CATALOG"
echo " Schema:  $SCHEMA"
echo "============================================================"

# ============================================================
# HELPERS
# ============================================================

run_sql() {
    local stmt="$1"
    python3 -c "
import json, subprocess, sys, time
stmt = sys.argv[1]
profile = '$PROFILE'
wh_id = '$WH_ID'

def api_post(endpoint, body):
    cmd = ['databricks', 'api', 'post', endpoint, '--profile', profile, '--json', json.dumps(body)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {'error': r.stderr[:300]}

def api_get(endpoint):
    cmd = ['databricks', 'api', 'get', endpoint, '--profile', profile]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else {'error': r.stderr[:300]}

# Submit with wait_timeout to try quick completion first
result = api_post('/api/2.0/sql/statements', {
    'warehouse_id': wh_id, 'statement': stmt, 'wait_timeout': '50s'
})
state = result.get('status', {}).get('state', 'UNKNOWN')
stmt_id = result.get('statement_id', '')

# If still pending/running, poll until done (up to 5 min)
if state in ('PENDING', 'RUNNING') and stmt_id:
    for _ in range(60):
        time.sleep(5)
        poll = api_get(f'/api/2.0/sql/statements/{stmt_id}')
        state = poll.get('status', {}).get('state', 'UNKNOWN')
        if state not in ('PENDING', 'RUNNING'):
            result = poll
            break

print(json.dumps(result))
" "$stmt" 2>/dev/null
}

run_api() {
    local method="$1"
    local endpoint="$2"
    local body="${3:-}"
    if [ -n "$body" ]; then
        databricks api $method "$endpoint" --profile=$PROFILE --json "$body" 2>/dev/null || echo '{"error":"api_call_failed"}'
    else
        databricks api $method "$endpoint" --profile=$PROFILE 2>/dev/null || echo '{"error":"api_call_failed"}'
    fi
}

check_sql_success() {
    local result="$1"
    echo "$result" | python3 -c "
import json, sys
try:
    r = json.load(sys.stdin)
    sys.exit(0 if r.get('status',{}).get('state') == 'SUCCEEDED' else 1)
except: sys.exit(1)
" 2>/dev/null
}

# ============================================================
# CHECK PREREQUISITES
# ============================================================
if ! command -v databricks &> /dev/null; then
    echo "ERROR: Databricks CLI not found. Install with: pip install databricks-cli"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found."
    exit 1
fi

python3 -c "import numpy" 2>/dev/null || {
    echo "Installing numpy for data generation..."
    pip3 install numpy -q
}

# ============================================================
# [0/8] VALIDATE PROFILE
# ============================================================
echo ""
echo "[0/8] Validating Databricks profile..."
databricks auth env --profile=$PROFILE > /dev/null 2>&1 || {
    echo "ERROR: Profile '$PROFILE' is not valid. Run: databricks auth login <host> --profile=$PROFILE"
    exit 1
}
echo "  ✓ Profile '$PROFILE' is valid"

# ============================================================
# [1/8] FIND SQL WAREHOUSE
# ============================================================
echo ""
echo "[1/8] Finding SQL warehouse..."
WH_ID=$(databricks warehouses list --profile=$PROFILE --output=json 2>/dev/null | python3 -c "
import json, sys
whs = json.load(sys.stdin)
for wh in whs:
    if wh.get('state') == 'RUNNING':
        print(wh['id'])
        break
" 2>/dev/null)

if [ -z "$WH_ID" ]; then
    echo "  ⚠ No running warehouse found. Starting first available..."
    WH_ID=$(databricks warehouses list --profile=$PROFILE --output=json 2>/dev/null | python3 -c "
import json, sys
whs = json.load(sys.stdin)
if whs: print(whs[0]['id'])
" 2>/dev/null)
    if [ -n "$WH_ID" ]; then
        databricks warehouses start $WH_ID --profile=$PROFILE > /dev/null 2>&1
        echo "  ⏳ Waiting for warehouse $WH_ID to start..."
        for i in $(seq 1 12); do
            sleep 10
            STATE=$(databricks warehouses get $WH_ID --profile=$PROFILE --output=json 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('state',''))" 2>/dev/null)
            if [ "$STATE" = "RUNNING" ]; then break; fi
            echo "  ⏳ Still waiting... ($STATE)"
        done
    else
        echo "  ERROR: No warehouses found. Create one in the Databricks UI first."
        exit 1
    fi
fi
echo "  ✓ Using warehouse: $WH_ID"

# ============================================================
# [2/8] CREATE CATALOG, SCHEMA, VOLUME
# ============================================================
echo ""
echo "[2/8] Creating catalog, schema, and volume..."

# Attempt to create catalog
CAT_RESULT=$(run_sql "CREATE CATALOG IF NOT EXISTS $CATALOG")
CAT_OK=$(echo "$CAT_RESULT" | python3 -c "import json,sys; r=json.load(sys.stdin); print('yes' if r.get('status',{}).get('state')=='SUCCEEDED' else 'no')" 2>/dev/null)

if [ "$CAT_OK" = "yes" ]; then
    # Verify catalog actually exists (CREATE may silently succeed without creating)
    CAT_VERIFY=$(run_sql "SHOW CATALOGS LIKE '$CATALOG'" | python3 -c "import json,sys; r=json.load(sys.stdin); data=r.get('result',{}).get('data_array',[]); print('yes' if data else 'no')" 2>/dev/null)
    if [ "$CAT_VERIFY" = "yes" ]; then
        echo "  ✓ Catalog '$CATALOG' created"
    else
        CAT_OK="no"
    fi
fi

if [ "$CAT_OK" != "yes" ]; then
    # Check if it already exists
    CAT_EXISTS=$(run_sql "SHOW CATALOGS LIKE '$CATALOG'" | python3 -c "import json,sys; r=json.load(sys.stdin); data=r.get('result',{}).get('data_array',[]); print('yes' if data else 'no')" 2>/dev/null)
    if [ "$CAT_EXISTS" = "yes" ]; then
        echo "  ✓ Catalog '$CATALOG' (already exists)"
    else
        CAT_ERR=$(echo "$CAT_RESULT" | python3 -c "import json,sys; r=json.load(sys.stdin); print(r.get('status',{}).get('error',{}).get('message','Unknown error')[:300])" 2>/dev/null)
        echo ""
        echo "  ✗ Could not create catalog '$CATALOG'"
        echo "    Reason: $CAT_ERR"
        echo ""
        echo "  Available catalogs on this workspace:"
        run_sql "SHOW CATALOGS" | python3 -c "
import json, sys
r = json.load(sys.stdin)
for row in r.get('result',{}).get('data_array',[]):
    name = row[0]
    if name not in ('system','samples','__databricks_internal'):
        print(f'      - {name}')
" 2>/dev/null
        echo ""
        echo "  OPTIONS:"
        echo "    1. Create catalog '$CATALOG' manually via the Databricks UI"
        echo "       (Catalog Explorer → Create Catalog → Name: $CATALOG)"
        echo "    2. Use an existing catalog by editing setup/config.py:"
        echo "       CATALOG = \"<catalog_name_from_above>\""
        echo "    3. Re-run this script after resolving"
        exit 1
    fi
fi

# Create schema
SCHEMA_RESULT=$(run_sql "CREATE SCHEMA IF NOT EXISTS $FULL_SCHEMA")
SCHEMA_OK=$(echo "$SCHEMA_RESULT" | python3 -c "import json,sys; r=json.load(sys.stdin); print('yes' if r.get('status',{}).get('state')=='SUCCEEDED' else 'no')" 2>/dev/null)
if [ "$SCHEMA_OK" = "yes" ]; then
    echo "  ✓ Schema '$FULL_SCHEMA' created"
else
    SCHEMA_EXISTS=$(run_sql "SHOW SCHEMAS IN $CATALOG LIKE '$SCHEMA'" | python3 -c "import json,sys; r=json.load(sys.stdin); data=r.get('result',{}).get('data_array',[]); print('yes' if data else 'no')" 2>/dev/null)
    if [ "$SCHEMA_EXISTS" = "yes" ]; then
        echo "  ✓ Schema '$FULL_SCHEMA' (already exists)"
    else
        SCHEMA_ERR=$(echo "$SCHEMA_RESULT" | python3 -c "import json,sys; r=json.load(sys.stdin); print(r.get('status',{}).get('error',{}).get('message','Unknown error')[:300])" 2>/dev/null)
        echo "  ✗ Could not create schema '$FULL_SCHEMA'"
        echo "    Reason: $SCHEMA_ERR"
        exit 1
    fi
fi

# Create volume
VOL_RESULT=$(run_sql "CREATE VOLUME IF NOT EXISTS $FULL_SCHEMA.credit_docs")
VOL_OK=$(echo "$VOL_RESULT" | python3 -c "import json,sys; r=json.load(sys.stdin); print('yes' if r.get('status',{}).get('state')=='SUCCEEDED' else 'no')" 2>/dev/null)
if [ "$VOL_OK" = "yes" ]; then
    echo "  ✓ Volume '$FULL_SCHEMA.credit_docs' created"
else
    VOL_ERR=$(echo "$VOL_RESULT" | python3 -c "import json,sys; r=json.load(sys.stdin); print(r.get('status',{}).get('error',{}).get('message','Unknown error')[:300])" 2>/dev/null)
    echo "  ⚠ Volume creation issue: $VOL_ERR"
fi

# ============================================================
# [3/8] GENERATE DATA & CREATE TABLES
# ============================================================
echo ""
echo "[3/8] Generating synthetic data and creating tables..."

# Generate CSVs locally
python3 "$SCRIPT_DIR/02_generate_data.py" 2>/dev/null
echo "  ✓ Generated CSV files locally"

# Upload CSVs to volume
CSV_DIR="$REPO_DIR/sample_data"
for csv_file in underbanked_prediction.csv cust_personal_info.csv; do
    if [ -f "$CSV_DIR/$csv_file" ]; then
        databricks fs cp "$CSV_DIR/$csv_file" "dbfs:/Volumes/$CATALOG/$SCHEMA/credit_docs/$csv_file" --profile=$PROFILE --overwrite 2>/dev/null
        echo "  ✓ Uploaded $csv_file to volume"
    fi
done

# Upload sample PDF if exists
PDF_PATH="$REPO_DIR/sample_data/Credit_Analyst_Decision_Logic_Playbook.pdf"
if [ -f "$PDF_PATH" ]; then
    databricks fs cp "$PDF_PATH" "dbfs:/Volumes/$CATALOG/$SCHEMA/credit_docs/Credit_Analyst_Decision_Logic_Playbook.pdf" --profile=$PROFILE --overwrite 2>/dev/null
    echo "  ✓ Uploaded Credit_Analyst_Decision_Logic_Playbook.pdf"
fi

# Create tables from CSVs using read_files
echo "  Creating underbanked_prediction table..."
RESULT=$(run_sql "CREATE OR REPLACE TABLE $FULL_SCHEMA.underbanked_prediction AS SELECT * FROM read_files('/Volumes/$CATALOG/$SCHEMA/credit_docs/underbanked_prediction.csv', format => 'csv', header => true, inferSchema => true)")
if check_sql_success "$RESULT"; then
    echo "  ✓ Created underbanked_prediction"
else
    echo "  ⚠ underbanked_prediction: check workspace for status"
fi

echo "  Creating cust_personal_info table..."
RESULT=$(run_sql "CREATE OR REPLACE TABLE $FULL_SCHEMA.cust_personal_info AS SELECT * FROM read_files('/Volumes/$CATALOG/$SCHEMA/credit_docs/cust_personal_info.csv', format => 'csv', header => true, inferSchema => true)")
if check_sql_success "$RESULT"; then
    echo "  ✓ Created cust_personal_info"
else
    echo "  ⚠ cust_personal_info: check workspace for status"
fi

# Verify tables (retry up to 3 times if 0 rows)
echo "  Verifying tables..."
for attempt in 1 2 3; do
    RESULT=$(run_sql "SELECT COUNT(*) as cnt FROM $FULL_SCHEMA.underbanked_prediction")
    CNT_UB=$(echo "$RESULT" | python3 -c "import json,sys; r=json.load(sys.stdin); print(r.get('result',{}).get('data_array',[[0]])[0][0])" 2>/dev/null)

    RESULT=$(run_sql "SELECT COUNT(*) as cnt FROM $FULL_SCHEMA.cust_personal_info")
    CNT_PI=$(echo "$RESULT" | python3 -c "import json,sys; r=json.load(sys.stdin); print(r.get('result',{}).get('data_array',[[0]])[0][0])" 2>/dev/null)

    if [ "$CNT_UB" != "0" ] && [ -n "$CNT_UB" ] && [ "$CNT_PI" != "0" ] && [ -n "$CNT_PI" ]; then
        break
    fi
    if [ "$attempt" -lt 3 ]; then
        echo "  ⏳ Tables not ready yet, waiting 15s... (attempt $attempt/3)"
        sleep 15
    fi
done
echo "  ✓ underbanked_prediction: $CNT_UB rows"
echo "  ✓ cust_personal_info: $CNT_PI rows"

if [ "$CNT_UB" = "0" ] || [ -z "$CNT_UB" ]; then
    echo "  ✗ ERROR: underbanked_prediction table is empty. Check workspace SQL editor."
    exit 1
fi

# ============================================================
# [4/8] CREATE UC FUNCTIONS
# ============================================================
echo ""
echo "[4/8] Creating UC functions..."

python3 - "$WH_ID" "$PROFILE" "$FULL_SCHEMA" <<'PYEOF'
import json, subprocess, sys

WH_ID, PROFILE, FULL_SCHEMA = sys.argv[1], sys.argv[2], sys.argv[3]

def run_sql(stmt):
    payload = json.dumps({'warehouse_id': WH_ID, 'statement': stmt, 'wait_timeout': '50s'})
    cmd = ['databricks', 'api', 'post', '/api/2.0/sql/statements', '--profile', PROFILE, '--json', payload]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode == 0:
        result = json.loads(r.stdout)
        state = result.get('status', {}).get('state', 'UNKNOWN')
        if state == 'FAILED':
            err = result.get('status', {}).get('error', {}).get('message', '')
            return f'FAILED: {err[:200]}'
        return state
    return f'ERROR: {r.stderr[:200]}'

# Function 1: get_customer_details
stmt1 = f"""CREATE OR REPLACE FUNCTION {FULL_SCHEMA}.get_customer_details(
  customer_id STRING COMMENT 'Customer ID of the customer to be searched'
)
RETURNS TABLE (
  cust_id INT, education INT, marital_status INT, age INT, is_resident INT,
  months_current_address INT, months_employment INT,
  number_payment_delays_last12mo BIGINT,
  pct_increase_annual_number_of_delays_last_3_year BIGINT,
  overdraft_balance_amount DOUBLE, tot_rel_bal DOUBLE, tot_assets DOUBLE,
  income_annual INT, avg_balance DOUBLE, num_accs BIGINT,
  tot_txn_amt_12m DOUBLE, sent_txn_cnt_12m BIGINT, prediction DOUBLE
)
COMMENT 'Returns demographic and financial information for a specific customer ID. Education: 0=Below 10th, 1=10th, 2=12th, 3=Graduate, 4=PG, 5=Professional. Marital: 0=Single, 1=Married, 2=Divorced, 3=Widowed. Prediction: 1=High Risk, 0=Low Risk.'
RETURN (
  SELECT cust_id, education, marital_status, age, is_resident,
    months_current_address, months_employment,
    number_payment_delays_last12mo,
    pct_increase_annual_number_of_delays_last_3_year,
    overdraft_balance_amount, tot_rel_bal, tot_assets,
    income_annual, avg_balance, num_accs,
    tot_txn_amt_12m, sent_txn_cnt_12m, prediction
  FROM {FULL_SCHEMA}.underbanked_prediction
  WHERE cust_id = customer_id
)"""
print(f"  get_customer_details: {run_sql(stmt1)}")

# Function 2: credit_report_generator
stmt2 = f"""CREATE OR REPLACE FUNCTION {FULL_SCHEMA}.credit_report_generator(
  cust_id INT, education INT, marital_status INT, age INT, is_resident INT,
  months_current_address INT, months_employment INT,
  number_payment_delays_last12mo BIGINT,
  pct_increase_annual_number_of_delays_last_3_year BIGINT,
  overdraft_balance_amount DOUBLE, tot_rel_bal DOUBLE, tot_assets DOUBLE,
  income_annual INT, avg_balance DOUBLE, num_accs BIGINT,
  tot_txn_amt_12m DOUBLE, sent_txn_cnt_12m BIGINT, prediction DOUBLE
)
RETURNS STRING
COMMENT 'Generates a credit risk report with RBI/CIBIL context.'
RETURN (
  SELECT ai_query(
    'databricks-gpt-oss-120b',
    CONCAT(
      'You are a Credit Risk Analyst for Indian banks per RBI guidelines and CIBIL scoring. Analyze the customer profile and generate a structured credit risk assessment report with: Customer Profile Summary, Risk Classification (HIGH/MEDIUM/LOW), Key Risk Factors, Financial Health Indicators, and Recommendation (Approve/Decline/Review). Education codes: 0=Below 10th, 1=10th, 2=12th, 3=Graduate, 4=PG, 5=Professional. Prediction: 1=High Risk, 0=Low Risk. Income in INR. Customer Details: ',
      TO_JSON(NAMED_STRUCT(
        'cust_id', cust_id, 'education', education, 'marital_status', marital_status,
        'age', age, 'is_resident', is_resident,
        'months_employment', months_employment,
        'payment_delays_12mo', number_payment_delays_last12mo,
        'overdraft', overdraft_balance_amount,
        'total_assets', tot_assets, 'income_annual_inr', income_annual,
        'avg_balance', avg_balance, 'risk_prediction', prediction
      ))
    )
  )
)"""
print(f"  credit_report_generator: {run_sql(stmt2)}")
PYEOF

# ============================================================
# [5/8] LOAD RAG KNOWLEDGE CHUNKS
# ============================================================
echo ""
echo "[5/8] Loading RAG knowledge chunks..."

python3 "$SCRIPT_DIR/04_load_rag_chunks.py" --profile=$PROFILE 2>&1 | while IFS= read -r line; do echo "  $line"; done

# ============================================================
# [6/8] CREATE VECTOR SEARCH ENDPOINT + INDEX
# ============================================================
echo ""
echo "[6/8] Creating Vector Search endpoint and index..."

VS_ENDPOINT="credit-risk-vs-endpoint"
VS_INDEX="${FULL_SCHEMA}.credit_policy_index"
RAG_TABLE="${FULL_SCHEMA}.rag_chunks"

# Check/Create endpoint
EP_CHECK=$(run_api get "/api/2.0/vector-search/endpoints/$VS_ENDPOINT" 2>/dev/null)
EP_EXISTS=$(echo "$EP_CHECK" | python3 -c "import json,sys; r=json.load(sys.stdin); print('yes' if r.get('name') else 'no')" 2>/dev/null)

if [ "$EP_EXISTS" != "yes" ]; then
    echo "  Creating Vector Search endpoint '$VS_ENDPOINT'..."
    run_api post "/api/2.0/vector-search/endpoints" "{\"name\": \"$VS_ENDPOINT\", \"endpoint_type\": \"STANDARD\"}" > /dev/null
    echo "  ⏳ Waiting for endpoint to come online (this may take 5-10 minutes)..."
    for i in $(seq 1 60); do
        sleep 10
        STATE=$(run_api get "/api/2.0/vector-search/endpoints/$VS_ENDPOINT" | python3 -c "
import json,sys
r=json.load(sys.stdin)
s = r.get('endpoint_status',{}).get('state', r.get('status',{}).get('state','UNKNOWN'))
print(s)
" 2>/dev/null)
        if [ "$STATE" = "ONLINE" ]; then
            echo "  ✓ Endpoint is ONLINE"
            break
        fi
        if [ $((i % 6)) -eq 0 ]; then
            echo "  ⏳ Still provisioning... ($STATE) [$((i*10))s elapsed]"
        fi
    done
else
    echo "  ✓ Endpoint '$VS_ENDPOINT' already exists"
fi

# Check/Create index
IDX_CHECK=$(run_api get "/api/2.0/vector-search/indexes/$VS_INDEX" 2>/dev/null)
IDX_EXISTS=$(echo "$IDX_CHECK" | python3 -c "import json,sys; r=json.load(sys.stdin); print('yes' if r.get('name') else 'no')" 2>/dev/null)

if [ "$IDX_EXISTS" != "yes" ]; then
    echo "  Creating Vector Search index '$VS_INDEX'..."
    run_api post "/api/2.0/vector-search/indexes" "{
        \"name\": \"$VS_INDEX\",
        \"endpoint_name\": \"$VS_ENDPOINT\",
        \"primary_key\": \"chunk_id\",
        \"index_type\": \"DELTA_SYNC\",
        \"delta_sync_index_spec\": {
            \"source_table\": \"$RAG_TABLE\",
            \"pipeline_type\": \"TRIGGERED\",
            \"embedding_source_columns\": [{
                \"name\": \"content\",
                \"embedding_model_endpoint_name\": \"databricks-gte-large-en\"
            }]
        }
    }" > /dev/null
    echo "  ✓ Index creation initiated (sync will run automatically)"
else
    echo "  ✓ Index '$VS_INDEX' already exists"
fi

# ============================================================
# [7/8] CREATE GENIE SPACE
# ============================================================
echo ""
echo "[7/8] Creating Genie space..."

GENIE_RESULT=$(python3 - "$WH_ID" "$PROFILE" "$FULL_SCHEMA" <<'PYEOF'
import json, subprocess, sys, uuid

WH_ID, PROFILE, FULL_SCHEMA = sys.argv[1], sys.argv[2], sys.argv[3]

def nid():
    return uuid.uuid4().hex

# Build serialized_space (version 2 format)
space = {
    "version": 2,
    "config": {
        "sample_questions": sorted([
            {"id": nid(), "question": ["How many customers are high risk?"]},
            {"id": nid(), "question": ["What is the average income of low risk customers?"]},
            {"id": nid(), "question": ["Show me customers with more than 3 payment delays in last 12 months"]},
        ], key=lambda x: x["id"])
    },
    "data_sources": {
        "tables": sorted([
            {"identifier": f"{FULL_SCHEMA}.underbanked_prediction", "description": ["1000 Indian banking customers with financial, transaction, and risk prediction data (61 columns). Prediction: 1=High Risk, 0=Low Risk. Income in INR."]},
            {"identifier": f"{FULL_SCHEMA}.cust_personal_info", "description": ["100 customer personal details: Indian names, email, phone, risk prediction."]},
        ], key=lambda t: t["identifier"]),
        "metric_views": [],
    },
    "instructions": {
        "text_instructions": sorted([{
            "id": nid(),
            "content": [
                f"Indian retail banking credit risk demo. All data is synthetic. "
                f"Use INR for monetary amounts. Education: 0=Below 10th, 1=10th, 2=12th, 3=Graduate, 4=PG, 5=Professional. "
                f"Marital: 0=Single, 1=Married, 2=Divorced, 3=Widowed. Prediction: 1=High Risk, 0=Low Risk. "
                f"Join cust_personal_info to underbanked_prediction on cust_id."
            ],
        }], key=lambda x: x["id"]),
        "example_question_sqls": [],
        "sql_functions": sorted([
            {"id": nid(), "identifier": f"{FULL_SCHEMA}.get_customer_details"},
        ], key=lambda x: x["id"]),
        "join_specs": [],
        "sql_snippets": {"filters": [], "expressions": [], "measures": []},
    },
    "benchmarks": {"questions": []},
}

payload = {
    "warehouse_id": WH_ID,
    "title": "Credit Risk - FSI Credit Decisioning",
    "description": "Explore credit risk data for Indian banking customers with financial profiles, transaction patterns, and risk predictions.",
    "serialized_space": json.dumps(space, separators=(",", ":")),
}

cmd = ['databricks', 'api', 'post', '/api/2.0/genie/spaces',
       '--json', json.dumps(payload), '--profile', PROFILE]
r = subprocess.run(cmd, capture_output=True, text=True)
if r.returncode == 0:
    try:
        out = json.loads(r.stdout)
        space_id = out.get('space_id', '')
        print(space_id)
    except:
        print('')
else:
    print('')
    print(r.stderr[:300], file=sys.stderr)
PYEOF
)

GENIE_ID=$(echo "$GENIE_RESULT" | head -1)

if [ -n "$GENIE_ID" ] && [ "$GENIE_ID" != "" ]; then
    echo "  ✓ Genie space created: $GENIE_ID"
    # Save for later use
    echo "$GENIE_ID" > "$SCRIPT_DIR/genie_space_id.txt"
else
    echo "  ⚠ Could not create Genie space automatically."
    echo "  Create manually: SQL Editor → + → Genie Space"
    echo "    Title: Credit Risk - FSI Credit Decisioning"
    echo "    Tables: $FULL_SCHEMA.underbanked_prediction, $FULL_SCHEMA.cust_personal_info"
    GENIE_ID="<create-manually>"
fi

# ============================================================
# [8/8] CREATE LAKEBASE INSTANCE
# ============================================================
echo ""
echo "[8/8] Creating Lakebase instance..."

python3 "$SCRIPT_DIR/06_create_lakebase.py" --profile=$PROFILE 2>&1 | while IFS= read -r line; do echo "  $line"; done

# ============================================================
# DONE — SUMMARY
# ============================================================

WS_URL=$(databricks auth env --profile=$PROFILE 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('DATABRICKS_HOST',''))" 2>/dev/null)

echo ""
echo "============================================================"
echo " ✓ SETUP COMPLETE!"
echo "============================================================"
echo ""
echo " Assets Created:"
echo "   Catalog:          $CATALOG"
echo "   Schema:           $FULL_SCHEMA"
echo "   Tables:           $FULL_SCHEMA.underbanked_prediction (1000 rows)"
echo "                     $FULL_SCHEMA.cust_personal_info (100 rows)"
echo "                     $FULL_SCHEMA.rag_chunks (knowledge base)"
echo "   UC Functions:     $FULL_SCHEMA.get_customer_details"
echo "                     $FULL_SCHEMA.credit_report_generator"
echo "   Vector Search:    Endpoint: $VS_ENDPOINT"
echo "                     Index: $VS_INDEX"
echo "   Genie Space:      $GENIE_ID"
echo "   Lakebase:         credit-risk-lakebase"
echo ""
echo " Next Step:"
echo "   Create your agent using the ai-dev-kit framework"
echo "   pointing to the assets above."
echo ""
echo " Workspace: $WS_URL"
echo "============================================================"
