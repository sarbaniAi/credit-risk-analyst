"""
Central configuration for Credit Risk Analyst Agent setup.
Modify these values for your environment.
"""

# ============================================================
# CATALOG & SCHEMA (will be created if not exist)
# ============================================================
CATALOG = "fsi_credit_agent"
SCHEMA = "agent_schema"

# ============================================================
# TABLE NAMES (created inside CATALOG.SCHEMA)
# ============================================================
TABLE_UNDERBANKED = "underbanked_prediction"
TABLE_PERSONAL_INFO = "cust_personal_info"

# Full paths (auto-computed)
FULL_TABLE_UNDERBANKED = f"{CATALOG}.{SCHEMA}.{TABLE_UNDERBANKED}"
FULL_TABLE_PERSONAL_INFO = f"{CATALOG}.{SCHEMA}.{TABLE_PERSONAL_INFO}"

# ============================================================
# VOLUME (for PDF knowledge docs)
# ============================================================
VOLUME_NAME = "credit_docs"
FULL_VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME_NAME}"

# ============================================================
# UC FUNCTIONS
# ============================================================
FUNC_GET_CUSTOMER = "get_customer_details"
FUNC_CREDIT_REPORT = "credit_report_generator"

# ============================================================
# AGENT / MODEL SERVING
# ============================================================
AGENT_MODEL = "databricks-GPT-OSS-120B"
AGENT_ENDPOINT_NAME = "credit-risk-agent-endpoint"

# ============================================================
# GENIE SPACE
# ============================================================
GENIE_SPACE_TITLE = "Credit Risk - FSI Credit Decisioning"

# ============================================================
# LAKEBASE (for app memory)
# ============================================================
LAKEBASE_INSTANCE_NAME = "credit-risk-lakebase"
LAKEBASE_DB = "databricks_postgres"

# ============================================================
# DATABRICKS APP
# ============================================================
APP_NAME = "credit-risk-analyst"

# ============================================================
# DATA GENERATION
# ============================================================
NUM_CUSTOMERS_FULL = 1000       # underbanked_prediction rows
NUM_CUSTOMERS_PERSONAL = 100    # cust_personal_info rows (subset)
RANDOM_SEED = 42

# ============================================================
# INDIAN BANKING CONTEXT
# ============================================================
INDIAN_CONTEXT = True  # Generate Indian names, CIBIL-like scores, INR amounts
