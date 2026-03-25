"""
01_create_catalog.py — Create Unity Catalog, schema, and volume.

Run as Databricks notebook or via CLI:
  databricks api post /api/2.0/sql/statements --profile=<profile> --json '{...}'
"""

# %%
import os

_catalog_env = os.environ.get("UC_CATALOG", "")
_schema_env = os.environ.get("UC_SCHEMA", "")

if _catalog_env and _schema_env:
    CATALOG, SCHEMA = _catalog_env, _schema_env
    VOLUME_NAME = os.environ.get("UC_VOLUME", "credit_docs")
else:
    try:
        from setup.config import CATALOG, SCHEMA, VOLUME_NAME
    except ImportError:
        try:
            from config import CATALOG, SCHEMA, VOLUME_NAME
        except ImportError:
            raise RuntimeError("Set UC_CATALOG and UC_SCHEMA env vars or ensure config.py is importable")

# %%
# Run in Databricks notebook or cluster
try:
    from pyspark.sql import SparkSession
    spark = SparkSession.builder.getOrCreate()

    spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
    print(f"✓ Catalog '{CATALOG}' ready")

    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}")
    print(f"✓ Schema '{CATALOG}.{SCHEMA}' ready")

    spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{VOLUME_NAME}")
    print(f"✓ Volume '{CATALOG}.{SCHEMA}.{VOLUME_NAME}' ready")

    print(f"\nVolume path: /Volumes/{CATALOG}/{SCHEMA}/{VOLUME_NAME}/")
    print("Upload credit policy PDFs to this volume.")

except ImportError:
    print("Not running in Databricks. Use CLI instead:")
    print(f"""
databricks api post /api/2.0/sql/statements --profile=<profile> --json '{{
  "warehouse_id": "<WH_ID>",
  "statement": "CREATE CATALOG IF NOT EXISTS {CATALOG}; CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}; CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.{VOLUME_NAME};",
  "wait_timeout": "30s"
}}'
""")
