"""
05_create_lakebase.py — Create Lakebase instance for app conversation memory.

Creates:
  1. Lakebase (Postgres) instance
  2. Memory tables (conversation_history, user_memories, conversation_summaries)

Run via Databricks CLI or as a notebook.
"""

import json
import subprocess
import sys
import time

import os

_lakebase_env = os.environ.get("LAKEBASE_INSTANCE_NAME", "")

if _lakebase_env:
    LAKEBASE_INSTANCE_NAME = _lakebase_env
    LAKEBASE_DB = os.environ.get("LAKEBASE_DB", "databricks_postgres")
else:
    try:
        from setup.config import LAKEBASE_INSTANCE_NAME, LAKEBASE_DB
    except ImportError:
        try:
            from config import LAKEBASE_INSTANCE_NAME, LAKEBASE_DB
        except ImportError:
            print("ERROR: Set LAKEBASE_INSTANCE_NAME env var or ensure config.py is importable")
            sys.exit(1)


def run_cli(args, profile=None):
    """Run a databricks CLI command and return parsed JSON."""
    cmd = ["databricks"] + args
    if profile:
        cmd.extend(["--profile", profile])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {"error": result.stderr[:500]}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"output": result.stdout.strip()}


def create_lakebase(profile=None):
    """Create Lakebase instance and memory tables."""

    print("=" * 60)
    print("Lakebase Setup for Credit Risk App Memory")
    print("=" * 60)

    # --------------------------------------------------------
    # Step 1: Create Lakebase instance
    # --------------------------------------------------------
    print(f"\n[1/3] Creating Lakebase instance '{LAKEBASE_INSTANCE_NAME}'...")

    # Check if instance exists
    result = run_cli([
        "api", "get", f"/api/2.0/lakebase/instances/{LAKEBASE_INSTANCE_NAME}"
    ], profile)

    if "error" not in result or "not found" in str(result.get("error", "")).lower():
        # Create instance
        create_result = run_cli([
            "api", "post", "/api/2.0/lakebase/instances",
            "--json", json.dumps({
                "name": LAKEBASE_INSTANCE_NAME,
                "capacity": "SMALL"
            })
        ], profile)

        if "error" in create_result:
            print(f"  ⚠ Error: {create_result['error']}")
            print("  Lakebase may not be available in this workspace.")
            print("  Alternative: Create Lakebase instance via the Databricks UI:")
            print(f"    SQL Editor → Create → Lakebase → Name: {LAKEBASE_INSTANCE_NAME}")
        else:
            print(f"  ✓ Lakebase instance '{LAKEBASE_INSTANCE_NAME}' creation initiated")
            print("  ⏳ Waiting for instance to be ready...")
            for _ in range(30):
                time.sleep(10)
                check = run_cli([
                    "api", "get", f"/api/2.0/lakebase/instances/{LAKEBASE_INSTANCE_NAME}"
                ], profile)
                state = check.get("state", "UNKNOWN")
                if state == "RUNNING":
                    print(f"  ✓ Lakebase instance is RUNNING")
                    break
            else:
                print("  ⚠ Instance still provisioning. Check status in the UI.")
    else:
        state = result.get("state", "UNKNOWN")
        print(f"  ✓ Lakebase instance already exists (state: {state})")

    # --------------------------------------------------------
    # Step 2: Create memory tables
    # --------------------------------------------------------
    print(f"\n[2/3] Creating memory tables in '{LAKEBASE_INSTANCE_NAME}'...")

    table_sql = """
-- Conversation history (full audit trail)
CREATE TABLE IF NOT EXISTS app_conversation_history (
    id SERIAL PRIMARY KEY,
    thread_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conv_thread ON app_conversation_history(thread_id);
CREATE INDEX IF NOT EXISTS idx_conv_user ON app_conversation_history(user_id);

-- User memories (long-term learned facts)
CREATE TABLE IF NOT EXISTS app_user_memories (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    memory_type VARCHAR(100) NOT NULL,
    memory_key VARCHAR(255) NOT NULL,
    memory_value TEXT NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, memory_type, memory_key)
);

CREATE INDEX IF NOT EXISTS idx_mem_user ON app_user_memories(user_id);

-- Conversation summaries (thread context)
CREATE TABLE IF NOT EXISTS app_conversation_summaries (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    thread_id VARCHAR(255) NOT NULL UNIQUE,
    summary TEXT,
    customer_ids TEXT,
    message_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sum_user ON app_conversation_summaries(user_id);
"""

    print("  SQL to execute in Lakebase:")
    print("  " + "-" * 50)
    for line in table_sql.strip().split("\n"):
        if line.strip():
            print(f"  {line}")
    print("  " + "-" * 50)

    # Try to execute via API
    print(f"\n  Attempting to execute via Lakebase API...")

    # Lakebase uses the database credential generation API
    cred_result = run_cli([
        "api", "post", "/api/2.0/lakebase/credentials",
        "--json", json.dumps({"instance_name": LAKEBASE_INSTANCE_NAME})
    ], profile)

    if "error" not in cred_result and "host" in cred_result:
        host = cred_result["host"]
        port = cred_result.get("port", 5432)
        user = cred_result.get("username", "")
        password = cred_result.get("password", "")
        print(f"  ✓ Got Lakebase credentials (host: {host})")

        try:
            import psycopg2
            conn = psycopg2.connect(
                host=host, port=port,
                dbname=LAKEBASE_DB,
                user=user, password=password,
                sslmode="require"
            )
            cur = conn.cursor()
            # Execute each statement separately
            for stmt in table_sql.split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)
            conn.commit()
            cur.close()
            conn.close()
            print("  ✓ All memory tables created successfully!")
        except ImportError:
            print("  ⚠ psycopg2 not installed. Install with: pip install psycopg2-binary")
            print("  Then run the SQL above manually in a Lakebase query editor.")
        except Exception as e:
            print(f"  ⚠ Connection error: {str(e)[:200]}")
            print("  Run the SQL above manually in a Lakebase query editor.")
    else:
        print("  ⚠ Could not get Lakebase credentials via API.")
        print("  Create tables manually via SQL Editor connected to Lakebase.")

    # --------------------------------------------------------
    # Step 3: Print app.yaml config
    # --------------------------------------------------------
    print(f"""
\n[3/3] App Configuration

  Update your app.yaml with:

  env:
    - LAKEBASE_INSTANCE_NAME: "{LAKEBASE_INSTANCE_NAME}"
    - LAKEBASE_DB: "{LAKEBASE_DB}"

  ✓ Lakebase setup complete!
""")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create Lakebase for Credit Risk App")
    parser.add_argument("--profile", default=None, help="Databricks CLI profile")
    args = parser.parse_args()
    create_lakebase(profile=args.profile)
