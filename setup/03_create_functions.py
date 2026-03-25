"""
03_create_functions.py — Create Unity Catalog functions for the agent.

Creates:
  1. get_customer_details — TABLE function to look up customer by ID
  2. credit_report_generator — SCALAR function using ai_query to generate credit reports
"""

# %%
try:
    from setup.config import CATALOG, SCHEMA, TABLE_UNDERBANKED, AGENT_MODEL
except ImportError:
    CATALOG = "fsi_credit_agent"
    SCHEMA = "agent_schema"
    TABLE_UNDERBANKED = "underbanked_prediction"
    AGENT_MODEL = "databricks-gpt-oss-120b"

FULL_SCHEMA = f"{CATALOG}.{SCHEMA}"

# ============================================================
# FUNCTION 1: get_customer_details
# ============================================================
SQL_GET_CUSTOMER_DETAILS = f"""
CREATE OR REPLACE FUNCTION {FULL_SCHEMA}.get_customer_details(
  customer_id STRING COMMENT 'Customer ID of the customer to be searched'
)
RETURNS TABLE (
  cust_id INT,
  education INT,
  marital_status INT,
  age INT,
  is_resident INT,
  months_current_address INT,
  months_employment INT,
  number_payment_delays_last12mo BIGINT,
  pct_increase_annual_number_of_delays_last_3_year BIGINT,
  overdraft_balance_amount DOUBLE,
  tot_rel_bal DOUBLE,
  tot_assets DOUBLE,
  income_annual INT,
  avg_balance DOUBLE,
  num_accs BIGINT,
  tot_txn_amt_12m DOUBLE,
  sent_txn_cnt_12m BIGINT,
  prediction DOUBLE
)
COMMENT 'Returns demographic and financial information for a specific customer ID. Education: 0=Below 10th, 1=10th, 2=12th, 3=Graduate, 4=PG, 5=Professional. Marital: 0=Single, 1=Married, 2=Divorced, 3=Widowed. Prediction: 1=High Risk, 0=Low Risk.'
RETURN (
  SELECT
    cust_id, education, marital_status, age, is_resident,
    months_current_address, months_employment,
    number_payment_delays_last12mo,
    pct_increase_annual_number_of_delays_last_3_year,
    overdraft_balance_amount, tot_rel_bal, tot_assets,
    income_annual, avg_balance, num_accs,
    tot_txn_amt_12m, sent_txn_cnt_12m, prediction
  FROM {FULL_SCHEMA}.{TABLE_UNDERBANKED}
  WHERE cust_id = customer_id
)
"""

# ============================================================
# FUNCTION 2: credit_report_generator
# ============================================================
SQL_CREDIT_REPORT_GENERATOR = f"""
CREATE OR REPLACE FUNCTION {FULL_SCHEMA}.credit_report_generator(
  cust_id INT,
  education INT,
  marital_status INT,
  age INT,
  is_resident INT,
  months_current_address INT,
  months_employment INT,
  number_payment_delays_last12mo BIGINT,
  pct_increase_annual_number_of_delays_last_3_year BIGINT,
  overdraft_balance_amount DOUBLE,
  tot_rel_bal DOUBLE,
  tot_assets DOUBLE,
  income_annual INT,
  avg_balance DOUBLE,
  num_accs BIGINT,
  tot_txn_amt_12m DOUBLE,
  sent_txn_cnt_12m BIGINT,
  prediction DOUBLE
)
RETURNS STRING
COMMENT 'Generates a credit risk report with RBI/CIBIL context based on customer details and financials. Prediction 1=High Risk, 0=Low Risk.'
RETURN (
  SELECT ai_query(
    '{AGENT_MODEL}',
    CONCAT(
      '
You are a Credit Risk Analyst Assistant for Indian banks, helping to identify Customer Credit Risk per RBI guidelines and CIBIL scoring standards.

### Context:
- Indian banking regulatory framework (RBI Master Directions on IRAC norms)
- CIBIL score ranges: 300-900 (750+ is good, below 650 is poor)
- Education: 0=Below 10th, 1=10th Pass, 2=12th Pass, 3=Graduate, 4=Post-Graduate, 5=Professional
- Marital Status: 0=Single, 1=Married, 2=Divorced, 3=Widowed
- Prediction: 1=High Credit Risk, 0=Low Credit Risk
- Income amounts are in INR

### Your Tasks:
1. Analyze the customer financial profile and risk indicators
2. If Prediction is 1 -> HIGH RISK, If Prediction is 0 -> LOW RISK
3. Generate a structured credit risk assessment report with:
   - Customer Profile Summary
   - Risk Classification (HIGH/MEDIUM/LOW)
   - Key Risk Factors identified
   - Financial Health Indicators
   - Recommendation (Approve/Decline/Review with conditions)

Structure the report professionally for a bank credit committee review.
',
      'Customer Details: ',
      TO_JSON(NAMED_STRUCT(
        'cust_id', cust_id,
        'education', education,
        'marital_status', marital_status,
        'age', age,
        'is_resident', is_resident,
        'months_current_address', months_current_address,
        'months_employment', months_employment,
        'number_payment_delays_last12mo', number_payment_delays_last12mo,
        'pct_increase_delays_3yr', pct_increase_annual_number_of_delays_last_3_year,
        'overdraft_balance_amount', overdraft_balance_amount,
        'total_relationship_balance', tot_rel_bal,
        'total_assets', tot_assets,
        'income_annual_inr', income_annual,
        'avg_balance', avg_balance,
        'num_accounts', num_accs,
        'total_txn_amount_12m', tot_txn_amt_12m,
        'sent_txn_count_12m', sent_txn_cnt_12m,
        'risk_prediction', prediction
      ))
    )
  )
)
"""

# %%
try:
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.getOrCreate()

    print("Creating UC functions...")

    spark.sql(SQL_GET_CUSTOMER_DETAILS)
    print(f"  ✓ Created {FULL_SCHEMA}.get_customer_details")

    spark.sql(SQL_CREDIT_REPORT_GENERATOR)
    print(f"  ✓ Created {FULL_SCHEMA}.credit_report_generator")

    # Test get_customer_details
    print("\nTesting get_customer_details(10000):")
    spark.sql(f"SELECT * FROM {FULL_SCHEMA}.get_customer_details('10000')").show()

    print("✓ All functions created successfully!")

except ImportError:
    print("Not running in Databricks. SQL statements to run manually:\n")
    print("-- Function 1: get_customer_details")
    print(SQL_GET_CUSTOMER_DETAILS)
    print("\n-- Function 2: credit_report_generator")
    print(SQL_CREDIT_REPORT_GENERATOR)
