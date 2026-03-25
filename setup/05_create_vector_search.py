"""
05_create_vector_search.py — Create Vector Search endpoint and index from rag_chunks table.

Prerequisites: Run 04_load_rag_chunks.py first to populate the rag_chunks table.

Creates:
  1. Vector Search endpoint
  2. Vector Search index (Delta Sync with managed embeddings from rag_chunks)

Run as a Databricks notebook.
"""

# %%
import os
try:
    from setup.config import CATALOG, SCHEMA
except ImportError:
    try:
        from config import CATALOG, SCHEMA
    except ImportError:
        CATALOG = os.environ.get("UC_CATALOG", "")
        SCHEMA = os.environ.get("UC_SCHEMA", "")
        if not CATALOG or not SCHEMA:
            raise RuntimeError("Set UC_CATALOG and UC_SCHEMA env vars or ensure config.py is importable")

FULL_SCHEMA = f"{CATALOG}.{SCHEMA}"
RAG_TABLE = f"{FULL_SCHEMA}.rag_chunks"
VS_ENDPOINT_NAME = "credit-risk-vs-endpoint"
VS_INDEX_NAME = f"{FULL_SCHEMA}.credit_policy_index"
EMBEDDING_MODEL = "databricks-gte-large-en"

# %%
from databricks.sdk import WorkspaceClient
import time

w = WorkspaceClient()

# ============================================================
# Step 1: Verify rag_chunks table exists
# ============================================================
print("Step 1: Verifying rag_chunks table...")
from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()

count = spark.sql(f"SELECT COUNT(*) FROM {RAG_TABLE}").collect()[0][0]
if count == 0:
    print(f"  ⚠ Table {RAG_TABLE} is empty. Run 04_load_rag_chunks.py first.")
    import sys
    sys.exit(0)
print(f"  ✓ {RAG_TABLE} has {count} chunks")

# %%
# ============================================================
# Step 2: Create Vector Search endpoint
# ============================================================
print("\nStep 2: Creating Vector Search endpoint...")

try:
    ep = w.vector_search_endpoints.get_endpoint(VS_ENDPOINT_NAME)
    print(f"  ✓ Endpoint '{VS_ENDPOINT_NAME}' already exists")
except Exception:
    print(f"  Creating endpoint '{VS_ENDPOINT_NAME}'...")
    w.vector_search_endpoints.create_endpoint(
        name=VS_ENDPOINT_NAME,
        endpoint_type="STANDARD"
    )
    print(f"  ✓ Endpoint creation initiated. Waiting for it to come online...")
    for _ in range(60):
        time.sleep(10)
        try:
            ep = w.vector_search_endpoints.get_endpoint(VS_ENDPOINT_NAME)
            if ep.status and ep.status.state and ep.status.state.value == "ONLINE":
                print(f"  ✓ Endpoint is ONLINE")
                break
        except Exception:
            pass
    else:
        print("  ⏳ Endpoint still provisioning. Check status in UI and re-run this cell.")

# %%
# ============================================================
# Step 3: Create Vector Search index (Delta Sync with managed embeddings)
# ============================================================
print("\nStep 3: Creating Vector Search index...")

try:
    idx = w.vector_search_indexes.get_index(VS_INDEX_NAME)
    print(f"  ✓ Index '{VS_INDEX_NAME}' already exists")
except Exception:
    print(f"  Creating index '{VS_INDEX_NAME}'...")
    from databricks.sdk.service.vectorsearch import (
        DeltaSyncVectorIndexSpecRequest,
        EmbeddingSourceColumn,
        PipelineType
    )

    w.vector_search_indexes.create_index(
        name=VS_INDEX_NAME,
        endpoint_name=VS_ENDPOINT_NAME,
        primary_key="chunk_id",
        index_type="DELTA_SYNC",
        delta_sync_index_spec=DeltaSyncVectorIndexSpecRequest(
            source_table=RAG_TABLE,
            pipeline_type=PipelineType.TRIGGERED,
            embedding_source_columns=[
                EmbeddingSourceColumn(
                    name="content",
                    embedding_model_endpoint_name=EMBEDDING_MODEL
                )
            ]
        )
    )
    print(f"  ✓ Index creation initiated. Sync will embed content from {RAG_TABLE}.")

# %%
print(f"""
✓ Vector Search Setup Complete!

  Endpoint:    {VS_ENDPOINT_NAME}
  Index:       {VS_INDEX_NAME}
  Source:      {RAG_TABLE}
  Embeddings:  {EMBEDDING_MODEL}

Use in your agent config:
  vector_search_endpoint = "{VS_ENDPOINT_NAME}"
  vector_search_index = "{VS_INDEX_NAME}"
""")
