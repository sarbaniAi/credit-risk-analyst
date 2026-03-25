#!/bin/bash
# ============================================================
# Credit Risk Analyst Agent — One-Command Setup
# ============================================================
#
# Usage:
#   ./setup/00_install.sh <databricks-profile>
#
# Example:
#   ./setup/00_install.sh my-workspace-profile
#
# This script runs locally and uploads notebooks to your
# Databricks workspace for execution.
# ============================================================

set -e

PROFILE=${1:-"DEFAULT"}
CATALOG="fsi_credit_agent"
SCHEMA="agent_schema"

echo "============================================================"
echo " Credit Risk Analyst Agent — Setup"
echo " Profile: $PROFILE"
echo " Catalog: $CATALOG"
echo " Schema:  $SCHEMA"
echo "============================================================"

# Check databricks CLI
if ! command -v databricks &> /dev/null; then
    echo "ERROR: Databricks CLI not found. Install with: pip install databricks-cli"
    exit 1
fi

# Validate profile
echo ""
echo "[0/6] Validating Databricks profile..."
databricks auth env --profile=$PROFILE > /dev/null 2>&1 || {
    echo "ERROR: Profile '$PROFILE' is not valid. Run: databricks auth login <host> --profile=$PROFILE"
    exit 1
}
echo "  ✓ Profile '$PROFILE' is valid"

# Get a running warehouse
echo ""
echo "[1/6] Finding SQL warehouse..."
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
        databricks warehouses start $WH_ID --profile=$PROFILE 2>/dev/null
        echo "  ⏳ Waiting for warehouse $WH_ID to start..."
        sleep 30
    else
        echo "  ERROR: No warehouses found. Create one in the Databricks UI first."
        exit 1
    fi
fi
echo "  ✓ Using warehouse: $WH_ID"

# Step 1: Create catalog, schema, volume
echo ""
echo "[2/6] Creating catalog, schema, and volume..."
databricks api post /api/2.0/sql/statements --profile=$PROFILE --json "{
  \"warehouse_id\": \"$WH_ID\",
  \"statement\": \"CREATE CATALOG IF NOT EXISTS $CATALOG\",
  \"wait_timeout\": \"30s\"
}" > /dev/null 2>&1
echo "  ✓ Catalog '$CATALOG'"

databricks api post /api/2.0/sql/statements --profile=$PROFILE --json "{
  \"warehouse_id\": \"$WH_ID\",
  \"statement\": \"CREATE SCHEMA IF NOT EXISTS $CATALOG.$SCHEMA\",
  \"wait_timeout\": \"30s\"
}" > /dev/null 2>&1
echo "  ✓ Schema '$CATALOG.$SCHEMA'"

databricks api post /api/2.0/sql/statements --profile=$PROFILE --json "{
  \"warehouse_id\": \"$WH_ID\",
  \"statement\": \"CREATE VOLUME IF NOT EXISTS $CATALOG.$SCHEMA.credit_docs\",
  \"wait_timeout\": \"30s\"
}" > /dev/null 2>&1
echo "  ✓ Volume '$CATALOG.$SCHEMA.credit_docs'"

# Step 2: Upload sample PDF to volume
echo ""
echo "[3/6] Uploading sample PDF to volume..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PDF_PATH="$SCRIPT_DIR/../sample_data/Credit_Analyst_Decision_Logic_Playbook.pdf"

if [ -f "$PDF_PATH" ]; then
    databricks fs cp "$PDF_PATH" "dbfs:/Volumes/$CATALOG/$SCHEMA/credit_docs/Credit_Analyst_Decision_Logic_Playbook.pdf" --profile=$PROFILE --overwrite 2>/dev/null
    echo "  ✓ Uploaded Credit_Analyst_Decision_Logic_Playbook.pdf"
else
    echo "  ⚠ PDF not found at $PDF_PATH. Upload manually to /Volumes/$CATALOG/$SCHEMA/credit_docs/"
fi

# Step 3: Upload and run data generation notebook
echo ""
echo "[4/6] Uploading setup notebooks to workspace..."
WORKSPACE_DIR="/Workspace/Users/$(databricks current-user me --profile=$PROFILE 2>/dev/null | python3 -c "import json,sys; print(json.load(sys.stdin).get('userName',''))" 2>/dev/null)/credit-risk-setup"

databricks workspace mkdirs "$WORKSPACE_DIR" --profile=$PROFILE 2>/dev/null || true

for script in 01_create_catalog.py 02_generate_data.py 03_create_functions.py 04_create_vector_search.py; do
    if [ -f "$SCRIPT_DIR/$script" ]; then
        databricks workspace import "$WORKSPACE_DIR/$script" --file="$SCRIPT_DIR/$script" --format=AUTO --language=PYTHON --overwrite --profile=$PROFILE 2>/dev/null
        echo "  ✓ Uploaded $script"
    fi
done

# Step 4: Create Lakebase
echo ""
echo "[5/6] Setting up Lakebase..."
python3 "$SCRIPT_DIR/05_create_lakebase.py" --profile=$PROFILE 2>/dev/null || {
    echo "  ⚠ Lakebase setup requires manual steps. See setup/05_create_lakebase.py"
}

echo ""
echo "[6/6] Setup complete!"
echo ""
echo "============================================================"
echo " NEXT STEPS"
echo "============================================================"
echo ""
echo " 1. Run notebooks in order in Databricks:"
echo "    $WORKSPACE_DIR/02_generate_data.py"
echo "    $WORKSPACE_DIR/03_create_functions.py"
echo "    $WORKSPACE_DIR/04_create_vector_search.py"
echo ""
echo " 2. Create your agent using the ai-dev-kit framework"
echo "    pointing to these assets:"
echo "    - Tables: $CATALOG.$SCHEMA.underbanked_prediction"
echo "              $CATALOG.$SCHEMA.cust_personal_info"
echo "    - Functions: $CATALOG.$SCHEMA.get_customer_details"
echo "                 $CATALOG.$SCHEMA.credit_report_generator"
echo "    - Vector Search: credit-risk-vs-endpoint"
echo "    - Lakebase: credit-risk-lakebase"
echo ""
echo " 3. Deploy the Databricks App:"
echo "    Update deploy-template/app.yaml with your values"
echo "    databricks apps deploy credit-risk-analyst --profile=$PROFILE"
echo ""
echo "============================================================"
