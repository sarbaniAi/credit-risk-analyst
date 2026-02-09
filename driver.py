# Databricks notebook source
# MAGIC %md
# MAGIC # Credit Risk Agent with Long-Term Memory (Lakebase)
# MAGIC
# MAGIC This notebook demonstrates a Credit Risk Agent with both short-term and long-term memory capabilities using Databricks Lakebase.
# MAGIC
# MAGIC **Memory Features:**
# MAGIC - **Short-term memory**: Conversation context within a session using LangGraph checkpoints
# MAGIC - **Long-term memory**: Key insights extracted across sessions stored in Lakebase PostgreSQL
# MAGIC
# MAGIC **Reference Documentation:**
# MAGIC - [AI Agent Memory](https://docs.databricks.com/aws/en/generative-ai/agent-framework/stateful-agents)
# MAGIC
# MAGIC ## Lakebase Configuration
# MAGIC - Instance Name: `sarbani-lakebase-demo`
# MAGIC - Instance ID: `f73e15d8-cd0a-406e-a94c-efe31f020841`

# COMMAND ----------

# MAGIC %pip install -U -qqqq backoff databricks-openai uv databricks-agents mlflow-skinny[databricks] langgraph langchain-core psycopg[binary,pool]
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test the Agent with Memory
# MAGIC 
# MAGIC First, let's test the agent locally to verify memory functionality.

# COMMAND ----------

from agent_with_memory import AGENT

# Test basic functionality
response1 = AGENT.predict({
    "input": [{"role": "user", "content": "How can you help me with credit risk analysis?"}],
    "custom_inputs": {
        "user_id": "sarbani.maiti@databricks.com",
        "thread_id": "test-thread-memory-001"
    }
})
print("Response 1:")
print(response1.model_dump(exclude_none=True))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Test Session Continuity (Short-term Memory)
# MAGIC 
# MAGIC The agent should remember the context from the previous message in the same thread.

# COMMAND ----------

# Continue the conversation in the same thread
response2 = AGENT.predict({
    "input": [{"role": "user", "content": "Please analyze credit risk for Customer ID: 93486"}],
    "custom_inputs": {
        "user_id": "sarbani.maiti@databricks.com",
        "thread_id": "test-thread-memory-001"  # Same thread
    }
})
print("Response 2 (same thread):")
print(response2.model_dump(exclude_none=True))

# COMMAND ----------

# Follow-up question in the same thread
response3 = AGENT.predict({
    "input": [{"role": "user", "content": "What were the main risk factors you identified for this customer?"}],
    "custom_inputs": {
        "user_id": "sarbani.maiti@databricks.com",
        "thread_id": "test-thread-memory-001"  # Same thread - should remember customer 93486
    }
})
print("Response 3 (follow-up in same thread):")
print(response3.model_dump(exclude_none=True))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Test Long-term Memory Across Sessions
# MAGIC 
# MAGIC Start a new thread and see if the agent remembers insights from previous sessions.

# COMMAND ----------

# New thread - should have long-term memory of previous interactions
response4 = AGENT.predict({
    "input": [{"role": "user", "content": "What customers have I analyzed recently?"}],
    "custom_inputs": {
        "user_id": "sarbani.maiti@databricks.com",
        "thread_id": "test-thread-memory-002"  # NEW thread
    }
})
print("Response 4 (new thread with long-term memory):")
print(response4.model_dump(exclude_none=True))

# COMMAND ----------

# MAGIC %md
# MAGIC ### View Stored Memories

# COMMAND ----------

# Get all memories for the user
user_memories = AGENT.get_user_memories("sarbani.maiti@databricks.com")
print("User Memories:")
print(json.dumps(user_memories, indent=2, default=str))

# COMMAND ----------

# MAGIC %md
# MAGIC ### View Checkpoint History (Time Travel)

# COMMAND ----------

# Get checkpoint history for time-travel debugging
import json
checkpoint_history = AGENT.get_checkpoint_history("test-thread-memory-001", limit=10)
print("Checkpoint History:")
print(json.dumps(checkpoint_history, indent=2, default=str))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Log the Agent with Memory
# MAGIC 
# MAGIC Register the memory-enabled agent to MLflow and Unity Catalog.

# COMMAND ----------

import mlflow
from agent_with_memory import LLM_ENDPOINT_NAME, uc_toolkit
from mlflow.models.resources import DatabricksFunction, DatabricksServingEndpoint
from pkg_resources import get_distribution

# Define resources for automatic auth passthrough
resources = [DatabricksServingEndpoint(endpoint_name=LLM_ENDPOINT_NAME)]
for tool in uc_toolkit.tools:
    udf_name = tool.get("function", {}).get("name", "").replace("__", ".")
    resources.append(DatabricksFunction(function_name=udf_name))

input_example = {
    "input": [
        {"role": "user", "content": "How can you help me?"}
    ],
    "custom_inputs": {
        "user_id": "test-user",
        "thread_id": "test-thread"
    }
}

with mlflow.start_run():
    logged_agent_info = mlflow.pyfunc.log_model(
        name="agent_with_memory",
        python_model="agent_with_memory.py",
        input_example=input_example,
        pip_requirements=[
            "databricks-openai",
            "backoff",
            "langgraph",
            "langchain-core",
            "psycopg[binary,pool]",
            f"databricks-connect=={get_distribution('databricks-connect').version}",
        ],
        resources=resources,
    )

print(f"Model logged with run_id: {logged_agent_info.run_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pre-deployment Validation

# COMMAND ----------

mlflow.models.predict(
    model_uri=f"runs:/{logged_agent_info.run_id}/agent_with_memory",
    input_data={
        "input": [{"role": "user", "content": "Hello!"}],
        "custom_inputs": {
            "user_id": "validation-user",
            "thread_id": "validation-thread"
        }
    },
    env_manager="uv",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Register to Unity Catalog

# COMMAND ----------

mlflow.set_registry_uri("databricks-uc")

# Define the catalog, schema, and model name
catalog = "sarbanimaiti_catalog"
schema = "fsi_credit"
model_name = "credit_risk_agent_with_memory"
UC_MODEL_NAME = f"{catalog}.{schema}.{model_name}"

# Register the model to UC
uc_registered_model_info = mlflow.register_model(
    model_uri=logged_agent_info.model_uri, name=UC_MODEL_NAME
)

print(f"Model registered to: {UC_MODEL_NAME}")
print(f"Version: {uc_registered_model_info.version}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Deploy the Agent

# COMMAND ----------

from databricks import agents

# Deploy with scale-to-zero for cost savings (not recommended for production)
agents.deploy(
    UC_MODEL_NAME, 
    uc_registered_model_info.version, 
    tags={"endpointSource": "memory-agent", "hasMemory": "true"}
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC 
# MAGIC After deployment:
# MAGIC 1. **Test in AI Playground**: Chat with the agent to verify memory functionality
# MAGIC 2. **Use the Memory App**: Deploy the frontend app in `08-DB-Memory-App` 
# MAGIC 3. **Monitor Memory Usage**: Check Lakebase tables for stored memories
# MAGIC 
# MAGIC ### Querying the Deployed Agent with Memory
# MAGIC 
# MAGIC To pass thread_id and user_id to the deployed endpoint:
# MAGIC 
# MAGIC ```python
# MAGIC from openai import OpenAI
# MAGIC 
# MAGIC client = OpenAI(
# MAGIC     api_key=databricks_token,
# MAGIC     base_url=f"https://{workspace_host}/serving-endpoints"
# MAGIC )
# MAGIC 
# MAGIC response = client.responses.create(
# MAGIC     model="credit_risk_agent_with_memory",
# MAGIC     input=[{"role": "user", "content": "Analyze customer 12345"}],
# MAGIC     extra_body={
# MAGIC         "custom_inputs": {
# MAGIC             "thread_id": "my-unique-thread-id",
# MAGIC             "user_id": "user@example.com"
# MAGIC         }
# MAGIC     }
# MAGIC )
# MAGIC ```
