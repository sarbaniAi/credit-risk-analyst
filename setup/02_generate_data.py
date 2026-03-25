"""
02_generate_data.py — Generate realistic Indian banking synthetic data.

Creates two Delta tables:
  1. underbanked_prediction — 1000 customers with financial, transaction, and risk data
  2. cust_personal_info — 100 customers with Indian names, emails, phones

Usage:
  databricks jobs submit --profile=<profile> --json '{
    "run_name": "generate-credit-data",
    "tasks": [{"task_key": "gen", "notebook_task": {"notebook_path": "/Workspace/setup/02_generate_data"}}]
  }'

  OR run as a Python script on a Databricks cluster/notebook.
"""

# %% [markdown]
# # Credit Risk Data Generation — Indian Banking Context

# %%
import random
import numpy as np
from datetime import datetime

# Import config
try:
    from setup.config import *
except ImportError:
    # Running as notebook — define inline
    CATALOG = "fsi_credit_agent"
    SCHEMA = "agent_schema"
    TABLE_UNDERBANKED = "underbanked_prediction"
    TABLE_PERSONAL_INFO = "cust_personal_info"
    NUM_CUSTOMERS_FULL = 1000
    NUM_CUSTOMERS_PERSONAL = 100
    RANDOM_SEED = 42

random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# ============================================================
# INDIAN NAMES DATABASE
# ============================================================
INDIAN_FIRST_NAMES_MALE = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan",
    "Krishna", "Ishaan", "Shaurya", "Atharva", "Advik", "Pranav", "Advait",
    "Dhruv", "Kabir", "Ritvik", "Aarush", "Kayaan", "Darsh", "Veer", "Sahil",
    "Rohan", "Arnav", "Lakshay", "Krish", "Parth", "Rudra", "Yash",
    "Rajesh", "Suresh", "Mahesh", "Ramesh", "Amit", "Ankit", "Gaurav",
    "Nikhil", "Rahul", "Vikram", "Sanjay", "Deepak", "Manoj", "Pradeep",
    "Harish", "Sunil", "Arun", "Kiran", "Naveen", "Ravi"
]

INDIAN_FIRST_NAMES_FEMALE = [
    "Aadhya", "Ananya", "Diya", "Saanvi", "Aanya", "Isha", "Pari", "Myra",
    "Sara", "Anika", "Navya", "Aarohi", "Kiara", "Riya", "Prisha",
    "Kavya", "Tara", "Zara", "Nisha", "Meera", "Sneha", "Pooja", "Swati",
    "Neha", "Anjali", "Sunita", "Rekha", "Priya", "Divya", "Lakshmi",
    "Shweta", "Pallavi", "Deepika", "Shruti", "Aishwarya", "Bhavna",
    "Chitra", "Gauri", "Jaya", "Kamala", "Leela", "Mala", "Padma",
    "Radha", "Sita", "Uma", "Vandana", "Yamini", "Zoya", "Aparna"
]

INDIAN_LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Patel", "Reddy",
    "Nair", "Iyer", "Mukherjee", "Chatterjee", "Banerjee", "Das",
    "Ghosh", "Bose", "Sen", "Pillai", "Menon", "Rao", "Naidu",
    "Joshi", "Kulkarni", "Deshmukh", "Patil", "Shinde", "Jadhav",
    "Mishra", "Pandey", "Tiwari", "Dubey", "Srivastava", "Agarwal",
    "Jain", "Mehta", "Shah", "Modi", "Trivedi", "Bhatt", "Dave",
    "Chauhan", "Rathore", "Yadav", "Thakur", "Rajput", "Malhotra",
    "Kapoor", "Khanna", "Chopra", "Bhatia", "Tandon"
]

INDIAN_EMAIL_DOMAINS = [
    "gmail.com", "yahoo.co.in", "outlook.com", "rediffmail.com",
    "hotmail.com", "sbi.co.in", "icicibank.com", "hdfcbank.com"
]

INDIAN_CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata",
    "Pune", "Ahmedabad", "Jaipur", "Lucknow", "Chandigarh", "Bhopal",
    "Indore", "Nagpur", "Coimbatore", "Kochi", "Vizag", "Patna",
    "Surat", "Vadodara", "Noida", "Gurgaon", "Thiruvananthapuram"
]

# ============================================================
# EDUCATION & MARITAL STATUS MAPPINGS (Indian context)
# ============================================================
# 0=Below 10th, 1=10th Pass, 2=12th Pass, 3=Graduate, 4=Post-Graduate, 5=Professional
EDUCATION_WEIGHTS = [0.05, 0.10, 0.20, 0.35, 0.20, 0.10]
MARITAL_WEIGHTS = [0.35, 0.55, 0.05, 0.05]  # 0=Single, 1=Married, 2=Divorced, 3=Widowed


def generate_indian_phone():
    """Generate Indian mobile number (+91 format)."""
    prefixes = ["70", "72", "73", "74", "75", "76", "77", "78", "79",
                "80", "81", "82", "83", "84", "85", "86", "87", "88", "89",
                "90", "91", "92", "93", "94", "95", "96", "97", "98", "99"]
    prefix = random.choice(prefixes)
    suffix = ''.join([str(random.randint(0, 9)) for _ in range(8)])
    return f"+91-{prefix}{suffix[:4]}-{suffix[4:]}"


def generate_customer_id(index):
    """Generate 5-digit customer ID."""
    return 10000 + index


def generate_personal_info(n):
    """Generate n customer personal info records with Indian names."""
    records = []
    for i in range(n):
        cust_id = generate_customer_id(i)
        is_male = random.random() < 0.55
        first_name = random.choice(INDIAN_FIRST_NAMES_MALE if is_male else INDIAN_FIRST_NAMES_FEMALE)
        last_name = random.choice(INDIAN_LAST_NAMES)
        domain = random.choice(INDIAN_EMAIL_DOMAINS)
        email = f"{first_name.lower()}.{last_name.lower()}{random.randint(1,99)}@{domain}"
        phone = generate_indian_phone()
        prediction = None  # Will be set after generating full data
        records.append({
            "cust_id": cust_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "mobile_phone": phone,
            "prediction": prediction
        })
    return records


def generate_underbanked_data(n):
    """Generate n customer financial records with Indian banking patterns."""
    records = []
    for i in range(n):
        cust_id = generate_customer_id(i)
        age = int(np.clip(np.random.normal(38, 12), 21, 70))
        education = int(np.random.choice(range(6), p=EDUCATION_WEIGHTS))
        marital_status = int(np.random.choice(range(4), p=MARITAL_WEIGHTS))
        is_resident = int(random.random() < 0.92)  # 92% resident Indians

        months_current_address = int(np.clip(np.random.exponential(48), 1, 360))
        months_employment = int(np.clip(np.random.exponential(60), 0, 480))
        tenure_months = int(np.clip(np.random.exponential(60), 1, 300))
        product_cnt = int(np.clip(np.random.poisson(3), 1, 12))

        # Indian income patterns (INR annual, in thousands for display but stored as int)
        # Range: 1.5L to 50L+ (150000 to 5000000+)
        if education >= 4:
            income_annual = int(np.clip(np.random.lognormal(13.5, 0.6), 500000, 10000000))
        elif education >= 3:
            income_annual = int(np.clip(np.random.lognormal(12.8, 0.7), 300000, 5000000))
        else:
            income_annual = int(np.clip(np.random.lognormal(12.0, 0.8), 150000, 3000000))

        tot_assets = int(income_annual * np.random.uniform(0.5, 8.0))

        # Balance and banking metrics (INR)
        tot_rel_bal = round(np.random.lognormal(9, 1.5), 2)
        avg_balance = round(np.random.lognormal(8, 1.2), 2)
        balance_usd = round(avg_balance / 83.5, 2)  # INR to USD approx
        available_balance_usd = round(balance_usd * np.random.uniform(0.1, 0.9), 2)
        num_accs = int(np.clip(np.random.poisson(2), 1, 8))

        # Revenue metrics
        revenue_tot = round(np.random.lognormal(7, 1.5), 2)
        revenue_12m = round(revenue_tot * np.random.uniform(0.1, 0.4), 2)
        customer_revenue = round(revenue_tot * np.random.uniform(0.5, 1.5), 2)

        # Overdraft
        has_overdraft = random.random() < 0.25
        overdraft_balance_amount = round(np.random.lognormal(12, 1.0), 2) if has_overdraft else 0.0
        overdraft_number = int(np.random.poisson(3)) if has_overdraft else 0

        # Deposits and equity
        total_deposits_number = int(np.clip(np.random.poisson(5), 0, 30))
        total_deposits_amount = round(np.random.lognormal(13, 1.5), 2)
        total_equity_amount = round(np.random.lognormal(13, 2.0), 2)
        total_UT = round(np.random.lognormal(13, 2.0), 2)

        is_pre_paid = int(random.random() < 0.08)

        # Payment delays (key risk indicator)
        delay_risk = 0.3 if income_annual < 400000 else 0.15 if income_annual < 800000 else 0.05
        number_payment_delays_last12mo = int(np.random.poisson(2 * delay_risk * 10))
        pct_increase_annual_number_of_delays_last_3_year = int(np.random.choice(
            [-4, -3, -2, -1, 0, 1, 2, 3, 4, 5],
            p=[0.05, 0.05, 0.10, 0.10, 0.30, 0.15, 0.10, 0.07, 0.05, 0.03]
        ))

        # Phone bill (INR)
        phone_bill_amt = round(np.random.choice([0, 199, 299, 399, 499, 599, 799, 999, 1499],
                                                 p=[0.05, 0.10, 0.15, 0.20, 0.20, 0.12, 0.08, 0.06, 0.04]), 2)
        avg_phone_bill_amt_lst12mo = round(phone_bill_amt * np.random.uniform(0.8, 1.2), 2)

        # UPI/NEFT Transaction patterns (very Indian)
        # 12-month windows
        dist_payer_cnt_12m = int(np.clip(np.random.poisson(5), 0, 30))
        sent_txn_cnt_12m = int(np.clip(np.random.poisson(48), 0, 500))
        sent_txn_amt_12m = round(sent_txn_cnt_12m * np.random.lognormal(7, 1.5), 2)
        sent_amt_avg_12m = round(sent_txn_amt_12m / max(sent_txn_cnt_12m, 1), 2)

        dist_payee_cnt_12m = int(np.clip(np.random.poisson(4), 0, 25))
        rcvd_txn_cnt_12m = int(np.clip(np.random.poisson(36), 0, 400))
        rcvd_txn_amt_12m = round(rcvd_txn_cnt_12m * np.random.lognormal(7.5, 1.5), 2)
        rcvd_amt_avg_12m = round(rcvd_txn_amt_12m / max(rcvd_txn_cnt_12m, 1), 2)

        # 6-month windows (roughly half of 12m)
        ratio_6m = np.random.uniform(0.4, 0.6)
        dist_payer_cnt_6m = int(dist_payer_cnt_12m * ratio_6m)
        sent_txn_cnt_6m = int(sent_txn_cnt_12m * ratio_6m)
        sent_txn_amt_6m = round(sent_txn_amt_12m * ratio_6m, 2)
        sent_amt_avg_6m = round(sent_txn_amt_6m / max(sent_txn_cnt_6m, 1), 2)
        dist_payee_cnt_6m = int(dist_payee_cnt_12m * ratio_6m)
        rcvd_txn_cnt_6m = int(rcvd_txn_cnt_12m * ratio_6m)
        rcvd_txn_amt_6m = round(rcvd_txn_amt_12m * ratio_6m, 2)
        rcvd_amt_avg_6m = round(rcvd_txn_amt_6m / max(rcvd_txn_cnt_6m, 1), 2)

        # 3-month windows (roughly quarter of 12m)
        ratio_3m = np.random.uniform(0.2, 0.35)
        dist_payer_cnt_3m = int(dist_payer_cnt_12m * ratio_3m)
        sent_txn_cnt_3m = int(sent_txn_cnt_12m * ratio_3m)
        sent_txn_amt_3m = round(sent_txn_amt_12m * ratio_3m, 2)
        sent_amt_avg_3m = round(sent_txn_amt_3m / max(sent_txn_cnt_3m, 1), 2)
        dist_payee_cnt_3m = int(dist_payee_cnt_12m * ratio_3m)
        rcvd_txn_cnt_3m = int(rcvd_txn_cnt_12m * ratio_3m)
        rcvd_txn_amt_3m = round(rcvd_txn_amt_12m * ratio_3m, 2)
        rcvd_amt_avg_3m = round(rcvd_txn_amt_3m / max(rcvd_txn_cnt_3m, 1), 2)

        # Totals
        tot_txn_cnt_12m = sent_txn_cnt_12m + rcvd_txn_cnt_12m
        tot_txn_amt_12m = round(sent_txn_amt_12m + rcvd_txn_amt_12m, 2)
        tot_txn_cnt_6m = sent_txn_cnt_6m + rcvd_txn_cnt_6m
        tot_txn_amt_6m = round(sent_txn_amt_6m + rcvd_txn_amt_6m, 2)
        tot_txn_cnt_3m = sent_txn_cnt_3m + rcvd_txn_cnt_3m
        tot_txn_amt_3m = round(sent_txn_amt_3m + rcvd_txn_amt_3m, 2)

        ratio_txn_amt_3m_12m = round(tot_txn_amt_3m / max(tot_txn_amt_12m, 1), 4)
        ratio_txn_amt_6m_12m = round(tot_txn_amt_6m / max(tot_txn_amt_12m, 1), 4)

        # PREDICTION (credit risk: 1=high risk, 0=low risk)
        # Risk factors: low income, payment delays, low assets, overdraft, low tenure
        risk_score = 0
        risk_score += 2.0 if income_annual < 400000 else (1.0 if income_annual < 800000 else 0)
        risk_score += 1.5 * min(number_payment_delays_last12mo, 5) / 5
        risk_score += 1.0 if tot_assets < 500000 else 0
        risk_score += 1.0 if has_overdraft and overdraft_balance_amount > 200000 else 0
        risk_score += 0.5 if tenure_months < 12 else 0
        risk_score += 0.5 if months_employment < 12 else 0
        risk_score += 0.5 if education < 2 else 0
        risk_score += 0.5 if pct_increase_annual_number_of_delays_last_3_year > 2 else 0
        noise = np.random.normal(0, 0.5)
        prediction = 1.0 if (risk_score + noise) > 3.0 else 0.0

        records.append({
            "cust_id": cust_id,
            "education": education,
            "marital_status": marital_status,
            "months_current_address": months_current_address,
            "months_employment": months_employment,
            "is_resident": is_resident,
            "tenure_months": tenure_months,
            "product_cnt": product_cnt,
            "tot_rel_bal": tot_rel_bal,
            "revenue_tot": revenue_tot,
            "revenue_12m": revenue_12m,
            "income_annual": income_annual,
            "tot_assets": tot_assets,
            "overdraft_balance_amount": overdraft_balance_amount,
            "overdraft_number": overdraft_number,
            "total_deposits_number": total_deposits_number,
            "total_deposits_amount": total_deposits_amount,
            "total_equity_amount": total_equity_amount,
            "total_UT": total_UT,
            "customer_revenue": customer_revenue,
            "age": age,
            "avg_balance": avg_balance,
            "num_accs": num_accs,
            "balance_usd": balance_usd,
            "available_balance_usd": available_balance_usd,
            "is_pre_paid": is_pre_paid,
            "number_payment_delays_last12mo": number_payment_delays_last12mo,
            "pct_increase_annual_number_of_delays_last_3_year": pct_increase_annual_number_of_delays_last_3_year,
            "phone_bill_amt": phone_bill_amt,
            "avg_phone_bill_amt_lst12mo": avg_phone_bill_amt_lst12mo,
            "dist_payer_cnt_12m": dist_payer_cnt_12m,
            "sent_txn_cnt_12m": sent_txn_cnt_12m,
            "sent_txn_amt_12m": sent_txn_amt_12m,
            "sent_amt_avg_12m": sent_amt_avg_12m,
            "dist_payee_cnt_12m": dist_payee_cnt_12m,
            "rcvd_txn_cnt_12m": rcvd_txn_cnt_12m,
            "rcvd_txn_amt_12m": rcvd_txn_amt_12m,
            "rcvd_amt_avg_12m": rcvd_amt_avg_12m,
            "dist_payer_cnt_6m": dist_payer_cnt_6m,
            "sent_txn_cnt_6m": sent_txn_cnt_6m,
            "sent_txn_amt_6m": sent_txn_amt_6m,
            "sent_amt_avg_6m": sent_amt_avg_6m,
            "dist_payee_cnt_6m": dist_payee_cnt_6m,
            "rcvd_txn_cnt_6m": rcvd_txn_cnt_6m,
            "rcvd_txn_amt_6m": rcvd_txn_amt_6m,
            "rcvd_amt_avg_6m": rcvd_amt_avg_6m,
            "dist_payer_cnt_3m": dist_payer_cnt_3m,
            "sent_txn_cnt_3m": sent_txn_cnt_3m,
            "sent_txn_amt_3m": sent_txn_amt_3m,
            "sent_amt_avg_3m": sent_amt_avg_3m,
            "dist_payee_cnt_3m": dist_payee_cnt_3m,
            "rcvd_txn_cnt_3m": rcvd_txn_cnt_3m,
            "rcvd_txn_amt_3m": rcvd_txn_amt_3m,
            "rcvd_amt_avg_3m": rcvd_amt_avg_3m,
            "tot_txn_cnt_12m": tot_txn_cnt_12m,
            "tot_txn_amt_12m": tot_txn_amt_12m,
            "tot_txn_cnt_6m": tot_txn_cnt_6m,
            "tot_txn_amt_6m": tot_txn_amt_6m,
            "tot_txn_cnt_3m": tot_txn_cnt_3m,
            "tot_txn_amt_3m": tot_txn_amt_3m,
            "ratio_txn_amt_3m_12m": ratio_txn_amt_3m_12m,
            "ratio_txn_amt_6m_12m": ratio_txn_amt_6m_12m,
            "prediction": prediction
        })
    return records


# %%
# ============================================================
# MAIN: Generate and write data
# ============================================================
if __name__ == "__main__" or "spark" in dir():
    print(f"Generating {NUM_CUSTOMERS_FULL} customer records (Indian banking context)...")

    # Generate data
    underbanked_data = generate_underbanked_data(NUM_CUSTOMERS_FULL)
    personal_data = generate_personal_info(NUM_CUSTOMERS_PERSONAL)

    # Set prediction in personal_info from underbanked data
    prediction_map = {r["cust_id"]: r["prediction"] for r in underbanked_data}
    for p in personal_data:
        p["prediction"] = prediction_map.get(p["cust_id"], 0.0)

    # Check if running in Databricks (Spark available)
    try:
        from pyspark.sql import SparkSession
        spark = SparkSession.builder.getOrCreate()

        # Create catalog and schema
        spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
        spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")

        # Create DataFrames
        df_underbanked = spark.createDataFrame(underbanked_data)
        df_personal = spark.createDataFrame(personal_data)

        # Write tables
        full_underbanked = f"{CATALOG}.{SCHEMA}.{TABLE_UNDERBANKED}"
        full_personal = f"{CATALOG}.{SCHEMA}.{TABLE_PERSONAL_INFO}"

        df_underbanked.write.format("delta").mode("overwrite").saveAsTable(full_underbanked)
        print(f"  ✓ Created {full_underbanked} ({len(underbanked_data)} rows)")

        df_personal.write.format("delta").mode("overwrite").saveAsTable(full_personal)
        print(f"  ✓ Created {full_personal} ({len(personal_data)} rows)")

        # Show sample
        print("\nSample underbanked_prediction:")
        spark.sql(f"SELECT cust_id, age, income_annual, tot_assets, prediction FROM {full_underbanked} LIMIT 5").show()

        print("Sample cust_personal_info:")
        spark.sql(f"SELECT * FROM {full_personal} LIMIT 5").show()

        # Stats
        high_risk = sum(1 for r in underbanked_data if r["prediction"] == 1.0)
        print(f"\nRisk distribution: {high_risk} high-risk ({high_risk*100/len(underbanked_data):.1f}%), "
              f"{len(underbanked_data)-high_risk} low-risk ({(len(underbanked_data)-high_risk)*100/len(underbanked_data):.1f}%)")

    except ImportError:
        # Not in Databricks — export as CSV for manual upload
        import csv
        import os

        output_dir = os.path.join(os.path.dirname(__file__), "..", "sample_data")
        os.makedirs(output_dir, exist_ok=True)

        # Write underbanked CSV
        csv_path = os.path.join(output_dir, "underbanked_prediction.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=underbanked_data[0].keys())
            writer.writeheader()
            writer.writerows(underbanked_data)
        print(f"  ✓ Wrote {csv_path} ({len(underbanked_data)} rows)")

        # Write personal info CSV
        csv_path = os.path.join(output_dir, "cust_personal_info.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=personal_data[0].keys())
            writer.writeheader()
            writer.writerows(personal_data)
        print(f"  ✓ Wrote {csv_path} ({len(personal_data)} rows)")

        print("\nCSV files generated. Upload to Databricks with:")
        print(f"  spark.read.csv('path/to/underbanked_prediction.csv', header=True, inferSchema=True)"
              f".write.saveAsTable('{CATALOG}.{SCHEMA}.{TABLE_UNDERBANKED}')")
