"""
04_load_rag_chunks.py — Load knowledge base markdown files into a Delta table for Vector Search.

Reads markdown files from setup/knowledge_docs/ and inserts them into
{CATALOG}.{SCHEMA}.rag_chunks for Vector Search indexing.

Usage: Run as Databricks notebook or via run_sql.py
"""

import os
import json
import subprocess
import sys

try:
    from setup.config import CATALOG, SCHEMA
except ImportError:
    try:
        from config import CATALOG, SCHEMA
    except ImportError:
        CATALOG = os.environ.get("UC_CATALOG", "")
        SCHEMA = os.environ.get("UC_SCHEMA", "")
        if not CATALOG or not SCHEMA:
            print("ERROR: Set UC_CATALOG and UC_SCHEMA env vars or ensure config.py is importable")
            sys.exit(1)

FULL_SCHEMA = f"{CATALOG}.{SCHEMA}"
RAG_TABLE = f"{FULL_SCHEMA}.rag_chunks"

# Locate knowledge docs
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE_DIR = os.path.join(SCRIPT_DIR, "knowledge_docs")


def load_chunks_spark():
    """Load chunks using Spark (run in Databricks notebook)."""
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.getOrCreate()

    # Create rag_chunks table
    spark.sql(f"""
        CREATE TABLE IF NOT EXISTS {RAG_TABLE} (
            chunk_id INT,
            source_path STRING,
            content STRING
        )
        TBLPROPERTIES (delta.enableChangeDataFeed = true)
    """)
    print(f"✓ Table {RAG_TABLE} ready")

    # Truncate existing data
    spark.sql(f"TRUNCATE TABLE {RAG_TABLE}")

    # Read and insert each markdown file
    md_files = sorted([f for f in os.listdir(KNOWLEDGE_DIR) if f.endswith(".md")])

    for idx, filename in enumerate(md_files, start=1):
        filepath = os.path.join(KNOWLEDGE_DIR, filename)
        with open(filepath, "r") as f:
            content = f.read()

        # Escape for SQL
        escaped = content.replace("'", "''").replace("\\", "\\\\")

        spark.sql(f"""
            INSERT INTO {RAG_TABLE}
            VALUES ({idx}, '{filename}', '{escaped}')
        """)
        print(f"  ✓ Loaded [{idx}] {filename} ({len(content)} chars)")

    total = spark.sql(f"SELECT COUNT(*) FROM {RAG_TABLE}").collect()[0][0]
    print(f"\n✓ {total} chunks loaded into {RAG_TABLE}")
    return total


def load_chunks_cli(profile=None):
    """Load chunks using Databricks CLI (run locally)."""

    # Find a running warehouse
    cmd = ["databricks", "warehouses", "list", "--output=json"]
    if profile:
        cmd.extend(["--profile", profile])
    result = subprocess.run(cmd, capture_output=True, text=True)
    wh_id = None
    if result.returncode == 0:
        for wh in json.loads(result.stdout):
            if wh.get("state") == "RUNNING":
                wh_id = wh["id"]
                break

    if not wh_id:
        print("ERROR: No running SQL warehouse found.")
        sys.exit(1)

    def run_sql(stmt):
        cmd = [
            "databricks", "api", "post", "/api/2.0/sql/statements",
            "--json", json.dumps({
                "warehouse_id": wh_id,
                "statement": stmt,
                "wait_timeout": "30s"
            })
        ]
        if profile:
            cmd.extend(["--profile", profile])
        r = subprocess.run(cmd, capture_output=True, text=True)
        return json.loads(r.stdout) if r.returncode == 0 else {"error": r.stderr}

    # Create table
    run_sql(f"""
        CREATE TABLE IF NOT EXISTS {RAG_TABLE} (
            chunk_id INT,
            source_path STRING,
            content STRING
        )
        TBLPROPERTIES (delta.enableChangeDataFeed = true)
    """)
    print(f"✓ Table {RAG_TABLE} ready")

    run_sql(f"TRUNCATE TABLE {RAG_TABLE}")

    # Load markdown files
    md_files = sorted([f for f in os.listdir(KNOWLEDGE_DIR) if f.endswith(".md")])

    for idx, filename in enumerate(md_files, start=1):
        filepath = os.path.join(KNOWLEDGE_DIR, filename)
        with open(filepath, "r") as f:
            content = f.read()

        escaped = content.replace("'", "''").replace("\\", "\\\\")
        result = run_sql(f"INSERT INTO {RAG_TABLE} VALUES ({idx}, '{filename}', '{escaped}')")
        if "error" in result:
            print(f"  ✗ Failed {filename}: {result['error'][:100]}")
        else:
            print(f"  ✓ Loaded [{idx}] {filename} ({len(content)} chars)")

    result = run_sql(f"SELECT COUNT(*) FROM {RAG_TABLE}")
    if "result" in result:
        total = result["result"]["data_array"][0][0]
        print(f"\n✓ {total} chunks loaded into {RAG_TABLE}")


if __name__ == "__main__":
    # Try Spark first (Databricks notebook), fall back to CLI
    try:
        load_chunks_spark()
    except Exception:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--profile", default=None)
        args = parser.parse_args()
        load_chunks_cli(profile=args.profile)
