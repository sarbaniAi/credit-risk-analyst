"""
Credit Risk Agent with Long-Term Memory using Databricks Lakebase
Based on: https://docs.databricks.com/aws/en/generative-ai/agent-framework/stateful-agents

This agent implements:
- Short-term memory: Conversation context within a session using LangGraph checkpoints
- Long-term memory: Key insights extracted across sessions stored in Lakebase
"""

import json
import logging
import os
import uuid
from typing import Any, Callable, Dict, Generator, List, Optional

import backoff
import mlflow
import openai
from databricks.sdk import WorkspaceClient
from databricks_openai import UCFunctionToolkit
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from mlflow.entities import SpanType
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
)
from openai import OpenAI
from pydantic import BaseModel
from unitycatalog.ai.core.base import get_uc_function_client
import psycopg

logger = logging.getLogger(__name__)

############################################
# Lakebase Configuration
############################################
LAKEBASE_INSTANCE_NAME = "sarbani-lakebase-demo"
LAKEBASE_INSTANCE_ID = "f73e15d8-cd0a-406e-a94c-efe31f020841"
LAKEBASE_CONNECTION_STRING = (
    f"postgresql://{{username}}:{{password}}@instance-{LAKEBASE_INSTANCE_ID}"
    ".database.azuredatabricks.net:5432/databricks_postgres?sslmode=require"
)

# Memory extraction prompt for long-term memory
MEMORY_EXTRACTION_PROMPT = """Based on the conversation, extract key information about the user that would be valuable to remember for future interactions.

Focus on:
- Customer IDs they frequently analyze
- Risk assessment preferences they've expressed
- Specific concerns or patterns they're interested in
- Any business context they've shared

Return the extracted memories as a JSON object with these fields:
- "customer_preferences": list of any customer-related preferences
- "analysis_patterns": list of analysis patterns or approaches they prefer
- "business_context": any relevant business context
- "key_insights": important insights from the conversation

If no memorable information was shared, return an empty JSON object {}."""

############################################
# LLM Configuration
############################################
LLM_ENDPOINT_NAME = "databricks-gpt-oss-120b"

SYSTEM_PROMPT = """You are a Credit Risk Analyst Assistant for banks, helping to identify Customer Credit Risk and report detailed, explainable decisions and recommendations.

{memory_context}

### Tools Available:
1. **get_customer_details** – Retrieves customer details, financials transaction history, and risk indicators for a given **Customer ID**.
2. **credit_risk_report_generator** - Generates a credit risk report based on the customer details retrieved.

### Your Tasks:
1. Retrieve customer financial and behavior information.
2. Analyze risk score, payment patterns, and financial health.
3. If Prediction is 1 -> Customer Credit Risk score is high, If Prediction is 0 -> Customer Credit Risk score is low.
4. Generate a concise decision report that explains the outcome and provides your recommendation.

Respond professionally and insightfully, structuring the report for easy consumption.
- Ensure all details match the provided **Customer ID** before proceeding.
- If the customer id is not present, briefly confirm that the customer is not present in the system.

If you have memory of previous interactions with this user, use that context to provide more personalized responses."""


############################################
# Tool Configuration
############################################
class ToolInfo(BaseModel):
    """Tool representation for the agent."""
    name: str
    spec: dict
    exec_fn: Callable

    class Config:
        arbitrary_types_allowed = True


def create_tool_info(tool_spec, exec_fn_param: Optional[Callable] = None):
    """Create a ToolInfo from a tool specification."""
    tool_spec["function"].pop("strict", None)
    tool_name = tool_spec["function"]["name"]
    udf_name = tool_name.replace("__", ".")

    def exec_fn(**kwargs):
        function_result = uc_function_client.execute_function(udf_name, kwargs)
        if function_result.error is not None:
            return function_result.error
        else:
            return function_result.value

    return ToolInfo(name=tool_name, spec=tool_spec, exec_fn=exec_fn_param or exec_fn)


# Initialize UC tools
UC_TOOL_NAMES = ["sarbanimaiti_catalog.fsi_credit.*"]
uc_toolkit = UCFunctionToolkit(function_names=UC_TOOL_NAMES)
uc_function_client = get_uc_function_client()

TOOL_INFOS = []
for tool_spec in uc_toolkit.tools:
    TOOL_INFOS.append(create_tool_info(tool_spec))


############################################
# Lakebase Memory Manager
############################################
class LakebaseMemoryManager:
    """Manages long-term memory storage in Databricks Lakebase."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._ensure_tables()

    def _get_connection(self):
        """Get a database connection using the Databricks token."""
        # Get token from environment or Databricks SDK
        try:
            ws = WorkspaceClient()
            token = ws.config.token
            username = ws.current_user.me().user_name
        except Exception:
            # Fallback to environment variables
            token = os.environ.get("DATABRICKS_TOKEN", "")
            username = os.environ.get("DATABRICKS_USERNAME", "sarbani.maiti@databricks.com")

        conn_str = self.connection_string.format(
            username=username.replace("@", "%40"),
            password=token
        )
        return psycopg.connect(conn_str)

    def _ensure_tables(self):
        """Create memory tables if they don't exist."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Long-term memory table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS agent_long_term_memory (
                            id SERIAL PRIMARY KEY,
                            user_id VARCHAR(255) NOT NULL,
                            memory_type VARCHAR(50) NOT NULL,
                            memory_key VARCHAR(255) NOT NULL,
                            memory_value TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(user_id, memory_type, memory_key)
                        )
                    """)

                    # Conversation summary table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS agent_conversation_summaries (
                            id SERIAL PRIMARY KEY,
                            user_id VARCHAR(255) NOT NULL,
                            thread_id VARCHAR(255) NOT NULL,
                            summary TEXT NOT NULL,
                            customer_ids_discussed TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(thread_id)
                        )
                    """)
                    conn.commit()
                    logger.info("Memory tables ensured")
        except Exception as e:
            logger.warning(f"Could not ensure tables (may already exist): {e}")

    def store_memory(self, user_id: str, memory_type: str, memory_key: str, memory_value: str):
        """Store or update a long-term memory."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO agent_long_term_memory (user_id, memory_type, memory_key, memory_value, updated_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (user_id, memory_type, memory_key) 
                        DO UPDATE SET memory_value = EXCLUDED.memory_value, updated_at = CURRENT_TIMESTAMP
                    """, (user_id, memory_type, memory_key, memory_value))
                    conn.commit()
                    logger.info(f"Stored memory: {memory_type}/{memory_key} for user {user_id}")
        except Exception as e:
            logger.error(f"Error storing memory: {e}")

    def get_memories(self, user_id: str, memory_type: Optional[str] = None) -> List[Dict]:
        """Retrieve memories for a user."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    if memory_type:
                        cur.execute("""
                            SELECT memory_type, memory_key, memory_value, updated_at
                            FROM agent_long_term_memory
                            WHERE user_id = %s AND memory_type = %s
                            ORDER BY updated_at DESC
                        """, (user_id, memory_type))
                    else:
                        cur.execute("""
                            SELECT memory_type, memory_key, memory_value, updated_at
                            FROM agent_long_term_memory
                            WHERE user_id = %s
                            ORDER BY updated_at DESC
                            LIMIT 50
                        """, (user_id,))
                    
                    rows = cur.fetchall()
                    return [
                        {
                            "memory_type": row[0],
                            "memory_key": row[1],
                            "memory_value": row[2],
                            "updated_at": str(row[3])
                        }
                        for row in rows
                    ]
        except Exception as e:
            logger.error(f"Error retrieving memories: {e}")
            return []

    def store_conversation_summary(self, user_id: str, thread_id: str, summary: str, customer_ids: List[str]):
        """Store a conversation summary."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO agent_conversation_summaries (user_id, thread_id, summary, customer_ids_discussed)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (thread_id) 
                        DO UPDATE SET summary = EXCLUDED.summary, customer_ids_discussed = EXCLUDED.customer_ids_discussed
                    """, (user_id, thread_id, summary, ",".join(customer_ids) if customer_ids else ""))
                    conn.commit()
        except Exception as e:
            logger.error(f"Error storing conversation summary: {e}")

    def get_recent_conversations(self, user_id: str, limit: int = 5) -> List[Dict]:
        """Get recent conversation summaries for a user."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT thread_id, summary, customer_ids_discussed, created_at
                        FROM agent_conversation_summaries
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (user_id, limit))
                    
                    rows = cur.fetchall()
                    return [
                        {
                            "thread_id": row[0],
                            "summary": row[1],
                            "customer_ids": row[2].split(",") if row[2] else [],
                            "created_at": str(row[3])
                        }
                        for row in rows
                    ]
        except Exception as e:
            logger.error(f"Error retrieving conversations: {e}")
            return []


############################################
# Credit Risk Agent with Memory (LangGraph)
############################################
class CreditRiskAgentWithMemory(ResponsesAgent):
    """
    Credit Risk Agent with both short-term and long-term memory.
    
    - Short-term: LangGraph checkpoints stored in Lakebase PostgreSQL
    - Long-term: Key insights extracted and stored across sessions
    """

    def __init__(self, llm_endpoint: str, tools: list[ToolInfo]):
        """Initialize the agent with memory capabilities."""
        self.llm_endpoint = llm_endpoint
        self.workspace_client = WorkspaceClient()
        self.model_serving_client: OpenAI = (
            self.workspace_client.serving_endpoints.get_open_ai_client()
        )
        self._tools_dict = {tool.name: tool for tool in tools}
        
        # Initialize memory manager
        self.memory_manager = LakebaseMemoryManager(LAKEBASE_CONNECTION_STRING)
        
        # Build the LangGraph
        self._graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        def call_model(state: MessagesState) -> Dict[str, Any]:
            """Call the LLM with the current messages."""
            messages = state["messages"]
            
            # Convert to OpenAI format
            openai_messages = []
            for msg in messages:
                if isinstance(msg, SystemMessage):
                    openai_messages.append({"role": "system", "content": msg.content})
                elif isinstance(msg, HumanMessage):
                    openai_messages.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AIMessage):
                    openai_messages.append({"role": "assistant", "content": msg.content})
            
            # Call LLM
            response = self.model_serving_client.chat.completions.create(
                model=self.llm_endpoint,
                messages=openai_messages,
                tools=self.get_tool_specs() if self._tools_dict else None,
            )
            
            choice = response.choices[0]
            
            # Handle tool calls
            if choice.message.tool_calls:
                # Execute tools and add results
                tool_results = []
                for tool_call in choice.message.tool_calls:
                    tool_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    result = self.execute_tool(tool_name, args)
                    tool_results.append(f"Tool {tool_name} result: {result}")
                
                return {
                    "messages": [AIMessage(content=choice.message.content or "\n".join(tool_results))]
                }
            
            return {"messages": [AIMessage(content=choice.message.content or "")]}

        # Build simple graph
        workflow = StateGraph(MessagesState)
        workflow.add_node("agent", call_model)
        workflow.add_edge(START, "agent")
        workflow.add_edge("agent", END)
        
        return workflow

    def get_tool_specs(self) -> list[dict]:
        """Returns tool specifications in OpenAI format."""
        return [tool_info.spec for tool_info in self._tools_dict.values()]

    @mlflow.trace(span_type=SpanType.TOOL)
    def execute_tool(self, tool_name: str, args: dict) -> Any:
        """Execute a tool by name."""
        if tool_name in self._tools_dict:
            return self._tools_dict[tool_name].exec_fn(**args)
        return f"Unknown tool: {tool_name}"

    def _format_memory_context(self, user_id: str) -> str:
        """Format long-term memories into context for the system prompt."""
        memories = self.memory_manager.get_memories(user_id)
        if not memories:
            return ""
        
        context_parts = ["### Previous Knowledge About This User:"]
        for mem in memories[:10]:  # Limit to 10 most recent
            context_parts.append(f"- {mem['memory_type']}: {mem['memory_key']} = {mem['memory_value']}")
        
        recent_convos = self.memory_manager.get_recent_conversations(user_id, limit=3)
        if recent_convos:
            context_parts.append("\n### Recent Conversation Summaries:")
            for conv in recent_convos:
                context_parts.append(f"- {conv['summary']}")
                if conv['customer_ids']:
                    context_parts.append(f"  (Discussed customers: {', '.join(conv['customer_ids'])})")
        
        return "\n".join(context_parts)

    def _extract_and_store_memories(self, user_id: str, thread_id: str, messages: List[Dict]):
        """Extract key information from conversation and store as long-term memory."""
        try:
            # Build conversation text
            conv_text = "\n".join([
                f"{m.get('role', 'unknown')}: {m.get('content', '')}"
                for m in messages[-10:]  # Last 10 messages
            ])
            
            # Use LLM to extract memories
            extraction_response = self.model_serving_client.chat.completions.create(
                model=self.llm_endpoint,
                messages=[
                    {"role": "system", "content": MEMORY_EXTRACTION_PROMPT},
                    {"role": "user", "content": f"Conversation:\n{conv_text}"}
                ],
                response_format={"type": "json_object"}
            )
            
            extracted = json.loads(extraction_response.choices[0].message.content or "{}")
            
            # Store extracted memories
            for mem_type, values in extracted.items():
                if isinstance(values, list):
                    for i, value in enumerate(values):
                        self.memory_manager.store_memory(
                            user_id, mem_type, f"{mem_type}_{i}", str(value)
                        )
                elif values:
                    self.memory_manager.store_memory(user_id, mem_type, mem_type, str(values))
            
            # Extract customer IDs mentioned
            customer_ids = []
            for msg in messages:
                content = msg.get("content", "")
                # Simple extraction - look for patterns like "customer 12345" or "Customer ID: 12345"
                import re
                matches = re.findall(r'customer\s*(?:id)?[:\s]*(\d{4,})', content.lower())
                customer_ids.extend(matches)
            
            # Create conversation summary
            if conv_text:
                summary_response = self.model_serving_client.chat.completions.create(
                    model=self.llm_endpoint,
                    messages=[
                        {"role": "system", "content": "Summarize this conversation in 1-2 sentences."},
                        {"role": "user", "content": conv_text}
                    ]
                )
                summary = summary_response.choices[0].message.content or "Conversation about credit risk"
                self.memory_manager.store_conversation_summary(
                    user_id, thread_id, summary, list(set(customer_ids))
                )
            
            logger.info(f"Extracted and stored memories for user {user_id}")
        except Exception as e:
            logger.warning(f"Memory extraction failed: {e}")

    def _get_checkpoint_saver(self):
        """Get a PostgreSQL checkpoint saver for short-term memory."""
        try:
            ws = WorkspaceClient()
            token = ws.config.token
            username = ws.current_user.me().user_name
        except Exception:
            token = os.environ.get("DATABRICKS_TOKEN", "")
            username = os.environ.get("DATABRICKS_USERNAME", "sarbani.maiti@databricks.com")
        
        conn_str = LAKEBASE_CONNECTION_STRING.format(
            username=username.replace("@", "%40"),
            password=token
        )
        return PostgresSaver.from_conn_string(conn_str)

    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        """Non-streaming prediction with memory."""
        # Extract user and thread IDs
        custom_inputs = dict(request.custom_inputs or {})
        user_id = custom_inputs.get("user_id", "default_user")
        thread_id = custom_inputs.get("thread_id", str(uuid.uuid4()))
        
        # Update custom inputs with generated thread_id
        if "thread_id" not in custom_inputs:
            custom_inputs["thread_id"] = thread_id
        
        # Set up MLflow tracing
        if thread_id:
            mlflow.update_current_trace(
                metadata={"mlflow.trace.session": thread_id}
            )
        
        # Get memory context
        memory_context = self._format_memory_context(user_id)
        
        # Prepare messages with memory-enhanced system prompt
        messages = []
        system_content = SYSTEM_PROMPT.format(memory_context=memory_context)
        messages.append({"role": "system", "content": system_content})
        
        for msg in request.input:
            msg_dict = msg.model_dump() if hasattr(msg, "model_dump") else dict(msg)
            messages.append({"role": msg_dict.get("role", "user"), "content": msg_dict.get("content", "")})
        
        # Call agent with tools
        outputs = []
        try:
            # Use checkpoint saver for short-term memory
            with self._get_checkpoint_saver() as checkpointer:
                graph = self._graph.compile(checkpointer=checkpointer)
                
                # Convert to LangChain messages
                lc_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        lc_messages.append(SystemMessage(content=msg["content"]))
                    elif msg["role"] == "user":
                        lc_messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        lc_messages.append(AIMessage(content=msg["content"]))
                
                config = {"configurable": {"thread_id": thread_id}}
                result = graph.invoke({"messages": lc_messages}, config)
                
                # Extract response
                if result.get("messages"):
                    last_msg = result["messages"][-1]
                    content = last_msg.content if hasattr(last_msg, "content") else str(last_msg)
                    outputs.append(self.create_text_output_item(content, str(uuid.uuid4())))
        
        except Exception as e:
            logger.warning(f"Checkpointing not available, using stateless mode: {e}")
            # Fallback to direct LLM call
            response = self.model_serving_client.chat.completions.create(
                model=self.llm_endpoint,
                messages=messages,
                tools=self.get_tool_specs() if self._tools_dict else None,
            )
            content = response.choices[0].message.content or ""
            outputs.append(self.create_text_output_item(content, str(uuid.uuid4())))
        
        # Extract and store long-term memories asynchronously
        try:
            self._extract_and_store_memories(user_id, thread_id, messages)
        except Exception as e:
            logger.warning(f"Memory storage failed: {e}")
        
        # Include thread_id and checkpoint info in outputs
        custom_outputs = {
            "thread_id": thread_id,
            "user_id": user_id,
            "memory_enabled": True
        }
        
        return ResponsesAgentResponse(output=outputs, custom_outputs=custom_outputs)

    def predict_stream(self, request: ResponsesAgentRequest) -> Generator[ResponsesAgentStreamEvent, None, None]:
        """Streaming prediction with memory."""
        # For simplicity, use non-streaming and yield at once
        response = self.predict(request)
        for item in response.output:
            yield ResponsesAgentStreamEvent(type="response.output_item.done", item=item)

    def get_checkpoint_history(self, thread_id: str, limit: int = 10) -> List[Dict]:
        """Retrieve checkpoint history for time-travel debugging."""
        try:
            with self._get_checkpoint_saver() as checkpointer:
                graph = self._graph.compile(checkpointer=checkpointer)
                config = {"configurable": {"thread_id": thread_id}}
                
                history = []
                for state in graph.get_state_history(config):
                    if len(history) >= limit:
                        break
                    history.append({
                        "checkpoint_id": state.config["configurable"]["checkpoint_id"],
                        "thread_id": thread_id,
                        "timestamp": str(state.created_at) if hasattr(state, "created_at") else None,
                        "message_count": len(state.values.get("messages", [])),
                    })
                return history
        except Exception as e:
            logger.error(f"Error getting checkpoint history: {e}")
            return []

    def get_user_memories(self, user_id: str) -> Dict[str, Any]:
        """Get all memories for a user (for debugging/display)."""
        return {
            "memories": self.memory_manager.get_memories(user_id),
            "recent_conversations": self.memory_manager.get_recent_conversations(user_id)
        }


# Initialize and register the agent
mlflow.openai.autolog()
AGENT = CreditRiskAgentWithMemory(llm_endpoint=LLM_ENDPOINT_NAME, tools=TOOL_INFOS)
mlflow.models.set_model(AGENT)
