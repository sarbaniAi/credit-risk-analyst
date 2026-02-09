"""
Credit Risk Chat App with External Memory Layer
Memory is handled OUTSIDE the agent - stored in Lakebase, injected into agent calls
Uses Databricks SDK for proper Lakebase authentication
"""

import os
import sys
import json
import logging
import requests
import uuid
from datetime import datetime
from flask import Flask, send_from_directory, request, jsonify, Response

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', stream=sys.stdout)
logger = logging.getLogger(__name__)

# Paths
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(APP_DIR, 'dist')

app = Flask(__name__, static_folder=DIST_DIR, static_url_path='')

# Config
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "https://adb-984752964297111.11.azuredatabricks.net")
SERVING_ENDPOINT = os.getenv("SERVING_ENDPOINT", "mas-8f9f5609-endpoint")

# Lakebase Config
LAKEBASE_INSTANCE_NAME = "sarbani-lakebase-demo"
LAKEBASE_DB = "databricks_postgres"

logger.info(f"Starting Memory-enabled Credit Risk App")
logger.info(f"Agent endpoint: {SERVING_ENDPOINT}")
logger.info(f"Lakebase instance: {LAKEBASE_INSTANCE_NAME}")

# In-memory fallback if Lakebase connection fails
MEMORY_CACHE = {
    "conversations": {},  # thread_id -> list of messages
    "user_memories": {},  # user_id -> list of memory items
    "summaries": {}       # user_id -> list of conversation summaries
}

# Cache for Lakebase connection info
_lakebase_cache = {
    "instance": None,
    "credential": None,
    "credential_time": None,
    "sp_identity": None
}


def get_lakebase_connection():
    """Get Lakebase PostgreSQL connection using Databricks SDK"""
    try:
        import psycopg2
        from databricks.sdk import WorkspaceClient
        
        logger.info("🔄 Attempting Lakebase connection...")
        
        # Initialize SDK (uses app's service principal credentials)
        w = WorkspaceClient()
        logger.info(f"SDK initialized, host: {w.config.host}, auth_type: {w.config.auth_type}")
        
        # Get the identity for connection
        # For service principals, try multiple approaches
        if _lakebase_cache.get("sp_identity") is None:
            identity = None
            
            # Approach 1: Try current_user.me()
            # For service principals, use user_name (client ID) as that's what's registered in Lakebase
            try:
                me = w.current_user.me()
                logger.info(f"current_user.me() result: user_name={me.user_name}, display_name={me.display_name}")
                # Use user_name (client ID) - this is what's registered as the role in Lakebase
                identity = me.user_name
                if identity:
                    logger.info(f"Using identity (user_name/client_id): {identity}")
            except Exception as e:
                logger.warning(f"current_user.me() failed: {e}")
            
            # Approach 2: For service principals, try the application_id from config
            if not identity:
                try:
                    # Service principals have client_id in config
                    client_id = getattr(w.config, 'client_id', None)
                    if client_id:
                        identity = client_id
                        logger.info(f"Using client_id: {identity}")
                except Exception as e:
                    logger.warning(f"Could not get client_id: {e}")
            
            # Approach 3: Hardcoded fallback for this specific app
            if not identity:
                identity = "39aa4b23-5c12-45bc-ab0a-8d0b855adfe9"  # App's service principal client ID
                logger.info(f"Using hardcoded client_id fallback: {identity}")
            
            _lakebase_cache["sp_identity"] = identity
        
        sp_identity = _lakebase_cache["sp_identity"]
        logger.info(f"Final identity for Lakebase: {sp_identity}")
        
        # Get instance info (cache it)
        if _lakebase_cache["instance"] is None:
            logger.info(f"Getting Lakebase instance: {LAKEBASE_INSTANCE_NAME}")
            _lakebase_cache["instance"] = w.database.get_database_instance(name=LAKEBASE_INSTANCE_NAME)
            logger.info(f"Got instance, DNS: {_lakebase_cache['instance'].read_write_dns}")
        
        instance = _lakebase_cache["instance"]
        
        # Generate credential (refresh if older than 30 minutes)
        now = datetime.now()
        if (_lakebase_cache["credential"] is None or 
            _lakebase_cache["credential_time"] is None or
            (now - _lakebase_cache["credential_time"]).seconds > 1800):
            
            logger.info("Generating new Lakebase credential...")
            _lakebase_cache["credential"] = w.database.generate_database_credential(
                request_id=str(uuid.uuid4()),
                instance_names=[LAKEBASE_INSTANCE_NAME]
            )
            _lakebase_cache["credential_time"] = now
            logger.info(f"Credential generated, token length: {len(_lakebase_cache['credential'].token)}")
        
        cred = _lakebase_cache["credential"]
        
        # Connect using psycopg2
        logger.info(f"Connecting to Lakebase: host={instance.read_write_dns}, user={sp_identity}")
        conn = psycopg2.connect(
            host=instance.read_write_dns,
            dbname=LAKEBASE_DB,
            user=sp_identity,
            password=cred.token,
            sslmode="require",
            connect_timeout=10
        )
        
        logger.info("✅ Lakebase connected successfully!")
        return conn
        
    except ImportError as e:
        logger.error(f"❌ IMPORT ERROR: {e} - psycopg2 not installed?")
        return None
    except Exception as e:
        logger.error(f"❌ LAKEBASE CONNECTION FAILED: {type(e).__name__}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def ensure_tables(conn):
    """Create memory tables if they don't exist"""
    if not conn:
        return
    try:
        with conn.cursor() as cur:
            # Conversation history table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_conversation_history (
                    id SERIAL PRIMARY KEY,
                    thread_id VARCHAR(255) NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Long-term memory table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_user_memories (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    memory_type VARCHAR(100) NOT NULL,
                    memory_key VARCHAR(255) NOT NULL,
                    memory_value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, memory_type, memory_key)
                )
            """)
            # Conversation summaries table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS app_conversation_summaries (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    thread_id VARCHAR(255) NOT NULL UNIQUE,
                    summary TEXT NOT NULL,
                    customer_ids TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            logger.info("Memory tables ensured")
    except Exception as e:
        logger.error(f"Error creating tables: {e}")


def store_message(conn, thread_id, user_id, role, content):
    """Store a message in conversation history"""
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO app_conversation_history (thread_id, user_id, role, content) VALUES (%s, %s, %s, %s)",
                    (thread_id, user_id, role, content)
                )
                conn.commit()
                logger.info(f"Stored message in Lakebase: {role} ({len(content)} chars)")
        except Exception as e:
            logger.error(f"Error storing message: {e}")
    
    # Also store in cache
    if thread_id not in MEMORY_CACHE["conversations"]:
        MEMORY_CACHE["conversations"][thread_id] = []
    MEMORY_CACHE["conversations"][thread_id].append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })


def get_conversation_history(conn, thread_id, limit=20):
    """Get conversation history for a thread"""
    messages = []
    
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT role, content FROM app_conversation_history WHERE thread_id = %s ORDER BY created_at DESC LIMIT %s",
                    (thread_id, limit)
                )
                rows = cur.fetchall()
                messages = [{"role": row[0], "content": row[1]} for row in reversed(rows)]
                logger.info(f"Retrieved {len(messages)} messages from Lakebase")
        except Exception as e:
            logger.error(f"Error getting history: {e}")
    
    # Fallback to cache
    if not messages and thread_id in MEMORY_CACHE["conversations"]:
        messages = [{"role": m["role"], "content": m["content"]} for m in MEMORY_CACHE["conversations"][thread_id][-limit:]]
    
    return messages


def store_user_memory(conn, user_id, memory_type, memory_key, memory_value):
    """Store a long-term memory for a user"""
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO app_user_memories (user_id, memory_type, memory_key, memory_value, updated_at)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id, memory_type, memory_key) 
                    DO UPDATE SET memory_value = EXCLUDED.memory_value, updated_at = CURRENT_TIMESTAMP
                """, (user_id, memory_type, memory_key, memory_value))
                conn.commit()
                logger.info(f"Stored memory: {memory_type}/{memory_key}")
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
    
    # Also store in cache
    if user_id not in MEMORY_CACHE["user_memories"]:
        MEMORY_CACHE["user_memories"][user_id] = []
    
    # Update or add
    found = False
    for mem in MEMORY_CACHE["user_memories"][user_id]:
        if mem["memory_type"] == memory_type and mem["memory_key"] == memory_key:
            mem["memory_value"] = memory_value
            found = True
            break
    if not found:
        MEMORY_CACHE["user_memories"][user_id].append({
            "memory_type": memory_type,
            "memory_key": memory_key,
            "memory_value": memory_value
        })


def get_user_memories(conn, user_id, limit=20):
    """Get long-term memories for a user"""
    memories = []
    
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT memory_type, memory_key, memory_value, updated_at FROM app_user_memories WHERE user_id = %s ORDER BY updated_at DESC LIMIT %s",
                    (user_id, limit)
                )
                memories = [
                    {"memory_type": row[0], "memory_key": row[1], "memory_value": row[2], "updated_at": str(row[3])}
                    for row in cur.fetchall()
                ]
                logger.info(f"Retrieved {len(memories)} memories from Lakebase")
        except Exception as e:
            logger.error(f"Error getting memories: {e}")
    
    # Fallback to cache
    if not memories and user_id in MEMORY_CACHE["user_memories"]:
        memories = MEMORY_CACHE["user_memories"][user_id][:limit]
    
    return memories


def store_conversation_summary(conn, user_id, thread_id, summary, customer_ids=None):
    """Store a conversation summary"""
    customer_ids_str = ",".join(customer_ids) if customer_ids else ""
    
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO app_conversation_summaries (user_id, thread_id, summary, customer_ids)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (thread_id) DO UPDATE SET summary = EXCLUDED.summary, customer_ids = EXCLUDED.customer_ids
                """, (user_id, thread_id, summary, customer_ids_str))
                conn.commit()
                logger.info(f"Stored conversation summary")
        except Exception as e:
            logger.error(f"Error storing summary: {e}")
    
    # Also store in cache
    if user_id not in MEMORY_CACHE["summaries"]:
        MEMORY_CACHE["summaries"][user_id] = []
    MEMORY_CACHE["summaries"][user_id].append({
        "thread_id": thread_id,
        "summary": summary,
        "customer_ids": customer_ids or []
    })


def get_conversation_summaries(conn, user_id, limit=5):
    """Get recent conversation summaries for a user"""
    summaries = []
    
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT thread_id, summary, customer_ids, created_at FROM app_conversation_summaries WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
                    (user_id, limit)
                )
                summaries = [
                    {
                        "thread_id": row[0],
                        "summary": row[1],
                        "customer_ids": row[2].split(",") if row[2] else [],
                        "created_at": str(row[3])
                    }
                    for row in cur.fetchall()
                ]
        except Exception as e:
            logger.error(f"Error getting summaries: {e}")
    
    # Fallback to cache
    if not summaries and user_id in MEMORY_CACHE["summaries"]:
        summaries = MEMORY_CACHE["summaries"][user_id][:limit]
    
    return summaries


def extract_customer_ids(text):
    """Extract customer IDs from text"""
    import re
    matches = re.findall(r'customer\s*(?:id)?[:\s]*(\d{4,})', text.lower())
    return list(set(matches))


def extract_emails(text):
    """Extract email addresses from text"""
    import re
    # Match email addresses
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    matches = re.findall(email_pattern, text)
    return list(set(matches))


def extract_memories_from_response(response_text, user_id, conn):
    """Extract and store key information from agent response"""
    import re
    
    # Extract customer IDs mentioned
    customer_ids = extract_customer_ids(response_text)
    for cid in customer_ids:
        store_user_memory(conn, user_id, "analyzed_customers", f"customer_{cid}", 
                         f"Analyzed on {datetime.now().strftime('%Y-%m-%d')}")
    
    # Extract risk levels mentioned
    if "high risk" in response_text.lower() or "high credit risk" in response_text.lower():
        for cid in customer_ids:
            store_user_memory(conn, user_id, "risk_assessments", f"customer_{cid}", "HIGH_RISK")
    elif "low risk" in response_text.lower() or "low credit risk" in response_text.lower():
        for cid in customer_ids:
            store_user_memory(conn, user_id, "risk_assessments", f"customer_{cid}", "LOW_RISK")
    elif "medium risk" in response_text.lower() or "moderate risk" in response_text.lower():
        for cid in customer_ids:
            store_user_memory(conn, user_id, "risk_assessments", f"customer_{cid}", "MEDIUM_RISK")
    
    # Extract email addresses and associate with customer IDs
    emails = extract_emails(response_text)
    if emails and customer_ids:
        for email in emails:
            for cid in customer_ids:
                store_user_memory(conn, user_id, "customer_emails", f"customer_{cid}", email)
                logger.info(f"Stored email {email} for customer {cid}")
    elif emails:
        for email in emails:
            store_user_memory(conn, user_id, "discovered_emails", email, 
                            f"Found on {datetime.now().strftime('%Y-%m-%d')}")
    
    # Extract customer names (patterns like "Name: John Smith" or "Customer name is John Smith")
    name_patterns = [
        r'(?:name|customer\s*name)[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',  # Name: John Smith
        r'(?:first\s*name)[:\s]+([A-Z][a-z]+)',  # First name: John
        r'(?:last\s*name)[:\s]+([A-Z][a-z]+)',   # Last name: Smith
    ]
    for pattern in name_patterns:
        matches = re.findall(pattern, response_text, re.IGNORECASE)
        if matches and customer_ids:
            for name in matches[:1]:  # Only first match
                for cid in customer_ids:
                    store_user_memory(conn, user_id, "customer_names", f"customer_{cid}", name)
                    logger.info(f"Stored name {name} for customer {cid}")
    
    # Extract financial data (income, balance, credit score, etc.)
    financial_patterns = [
        (r'(?:income|annual\s*income)[:\s]*\$?([\d,]+(?:\.\d{2})?)', "income"),
        (r'(?:credit\s*score|fico)[:\s]*(\d{3})', "credit_score"),
        (r'(?:balance|account\s*balance)[:\s]*\$?([\d,]+(?:\.\d{2})?)', "balance"),
        (r'(?:total\s*assets)[:\s]*\$?([\d,]+(?:\.\d{2})?)', "total_assets"),
        (r'(?:age)[:\s]*(\d{1,3})(?:\s*years)?', "age"),
    ]
    for pattern, data_type in financial_patterns:
        matches = re.findall(pattern, response_text, re.IGNORECASE)
        if matches and customer_ids:
            for value in matches[:1]:  # Only first match
                for cid in customer_ids:
                    store_user_memory(conn, user_id, f"customer_{data_type}", f"customer_{cid}", str(value))
                    logger.info(f"Stored {data_type}={value} for customer {cid}")


def build_memory_context(conn, user_id, thread_id):
    """Build CONCISE memory context - just key facts the agent can reference silently"""
    
    # Get user memories
    memories = get_user_memories(conn, user_id, limit=50)
    if not memories:
        return ""
    
    # Group memories by customer
    customer_data = {}
    for m in memories:
        if m["memory_key"].startswith("customer_"):
            cid = m["memory_key"].replace("customer_", "")
            if cid not in customer_data:
                customer_data[cid] = {}
            customer_data[cid][m["memory_type"]] = m["memory_value"]
    
    if not customer_data:
        return ""
    
    # Build MINIMAL context - just customer ID and key identifiers
    context_lines = []
    for cid, data in list(customer_data.items())[:5]:  # Only last 5 customers
        # Only include email (most likely to be asked about)
        if "customer_emails" in data:
            context_lines.append(f"customer_{cid}_email={data['customer_emails']}")
        if "risk_assessments" in data:
            context_lines.append(f"customer_{cid}_risk={data['risk_assessments']}")
    
    if context_lines:
        return "|".join(context_lines)
    return ""


def extract_token(req):
    """Extract token from various sources for agent calls"""
    auth_header = req.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    
    token = req.headers.get('X-Databricks-Token')
    if token:
        return token
    
    if req.json and req.json.get('_auth_token'):
        return req.json.get('_auth_token')
    
    try:
        from databricks.sdk import WorkspaceClient
        w = WorkspaceClient()
        return w.config.token
    except:
        pass
    
    return None


@app.route('/')
def serve_index():
    return send_from_directory(DIST_DIR, 'index.html')


@app.route('/api/serving-endpoints/<path:endpoint_path>', methods=['POST'])
def proxy_endpoint(endpoint_path):
    """Proxy to agent with memory injection"""
    logger.info(f"=== Agent request with memory ===")
    
    try:
        token = extract_token(request)
        if not token:
            return jsonify({"error": "Authentication required", "detail": "No token found"}), 401
        
        payload = request.json.copy() if request.json else {}
        payload.pop('_auth_token', None)
        
        # Get user_id and thread_id from custom_inputs
        custom_inputs = payload.get('custom_inputs', {})
        user_id = custom_inputs.get('user_id', 'default_user')
        thread_id = custom_inputs.get('thread_id', 'default_thread')
        
        logger.info(f"User: {user_id}, Thread: {thread_id}")
        
        # Connect to Lakebase using SDK credentials (service principal)
        conn = get_lakebase_connection()
        if conn:
            ensure_tables(conn)
            logger.info("🧠 Lakebase memory ACTIVE")
        else:
            logger.info("⚠️ Using in-memory fallback")
        
        # Get input messages
        input_messages = payload.get('input', [])
        
        # Store the new user message
        if input_messages:
            last_user_msg = next((m for m in reversed(input_messages) if m.get('role') == 'user'), None)
            if last_user_msg:
                store_message(conn, thread_id, user_id, 'user', last_user_msg.get('content', ''))
        
        # Build memory context
        memory_context = build_memory_context(conn, user_id, thread_id)
        
        # Get conversation history from this thread
        history = get_conversation_history(conn, thread_id, limit=10)
        
        # Build enhanced input with memory
        enhanced_input = []
        
        # Add memory context as a SILENT reference (agent should NOT repeat this)
        if memory_context:
            enhanced_input.append({
                "role": "user", 
                "content": f"[INTERNAL_REFERENCE_ONLY: {memory_context}] DO NOT mention or repeat this reference. Just use it if the user asks about 'my customer' or previous analysis. Answer ONLY the new question directly and concisely."
            })
        
        # Add conversation history (for short-term memory within thread)
        if history and len(history) > 1:
            # Add previous messages as context
            for msg in history[:-1]:  # Exclude the last one (current message)
                enhanced_input.append(msg)
        
        # Add the current user message(s)
        for msg in input_messages:
            enhanced_input.append(msg)
        
        # Update payload with enhanced input
        payload['input'] = enhanced_input
        
        logger.info(f"Sending {len(enhanced_input)} messages to agent (with memory context)")
        
        # Call the agent
        target_url = f"{DATABRICKS_HOST}/serving-endpoints/{endpoint_path}"
        resp = requests.post(
            target_url,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}'
            },
            json=payload,
            timeout=120
        )
        
        logger.info(f"Agent response: {resp.status_code}")
        
        # Process response and extract memories
        if resp.status_code == 200:
            try:
                response_data = resp.json()
                
                # Extract text from response
                response_text = ""
                if response_data.get('output'):
                    for item in response_data['output']:
                        if item.get('type') == 'message' and item.get('content'):
                            for c in item['content']:
                                if c.get('type') in ['output_text', 'text']:
                                    response_text += c.get('text', '')
                
                # Store assistant response
                if response_text:
                    store_message(conn, thread_id, user_id, 'assistant', response_text[:2000])
                    
                    # Extract and store memories
                    extract_memories_from_response(response_text, user_id, conn)
                    
                    # Create conversation summary (simple version)
                    customer_ids = extract_customer_ids(response_text)
                    if customer_ids:
                        summary = f"Analyzed customers: {', '.join(customer_ids[:3])}"
                        store_conversation_summary(conn, user_id, thread_id, summary, customer_ids)
                
                # Add memory indicator to response
                custom_outputs = response_data.get('custom_outputs') or {}
                custom_outputs['memory_enabled'] = True
                custom_outputs['memory_storage'] = "lakebase" if conn else "in_memory"
                custom_outputs['thread_id'] = thread_id
                custom_outputs['user_id'] = user_id
                response_data['custom_outputs'] = custom_outputs
                
                if conn:
                    conn.close()
                
                return jsonify(response_data)
                
            except Exception as e:
                logger.error(f"Error processing response: {e}")
        
        if conn:
            conn.close()
        
        return Response(resp.content, status=resp.status_code,
                       content_type=resp.headers.get('Content-Type', 'application/json'))
        
    except Exception as e:
        logger.exception(f"Proxy error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/memory/user/<user_id>', methods=['GET'])
def get_memories_api(user_id):
    """Get all memories for a user"""
    conn = get_lakebase_connection()
    
    memories = get_user_memories(conn, user_id)
    summaries = get_conversation_summaries(conn, user_id)
    
    storage_type = "lakebase" if conn else "in_memory"
    
    if conn:
        conn.close()
    
    return jsonify({
        "user_id": user_id,
        "memories": memories,
        "conversations": summaries,
        "storage": storage_type
    })


@app.route('/api/memory/user/<user_id>/clear', methods=['POST'])
def clear_memories_api(user_id):
    """Clear long-term memories for a user (keeps conversation history for audit)"""
    conn = get_lakebase_connection()
    
    if conn:
        try:
            with conn.cursor() as cur:
                # Clear long-term memories only
                cur.execute("DELETE FROM app_user_memories WHERE user_id = %s", (user_id,))
                cur.execute("DELETE FROM app_conversation_summaries WHERE user_id = %s", (user_id,))
                # NOTE: Keeping app_conversation_history for audit trail
                conn.commit()
            conn.close()
            logger.info(f"Cleared long-term memories for user: {user_id} (history preserved)")
        except Exception as e:
            logger.error(f"Error clearing memories: {e}")
            return jsonify({"error": str(e)}), 500
    
    # Clear cache too
    MEMORY_CACHE["user_memories"].pop(user_id, None)
    MEMORY_CACHE["summaries"].pop(user_id, None)
    
    return jsonify({"status": "cleared", "user_id": user_id, "history_preserved": True})


@app.route('/api/memory/thread/<thread_id>', methods=['GET'])
def get_thread_history_api(thread_id):
    """Get conversation history for a thread"""
    conn = get_lakebase_connection()
    history = get_conversation_history(conn, thread_id)
    
    if conn:
        conn.close()
    
    return jsonify({
        "thread_id": thread_id,
        "messages": history
    })


@app.route('/api/memory/user/<user_id>/threads', methods=['GET'])
def get_user_threads_api(user_id):
    """Get all conversation threads for a user"""
    conn = get_lakebase_connection()
    threads = []
    
    if conn:
        try:
            with conn.cursor() as cur:
                # Get distinct threads with their first message and timestamp
                cur.execute("""
                    SELECT DISTINCT ON (thread_id) 
                        thread_id, 
                        content,
                        created_at,
                        (SELECT COUNT(*) FROM app_conversation_history h2 WHERE h2.thread_id = h1.thread_id) as message_count
                    FROM app_conversation_history h1
                    WHERE user_id = %s AND role = 'user'
                    ORDER BY thread_id, created_at ASC
                """, (user_id,))
                
                rows = cur.fetchall()
                for row in rows:
                    threads.append({
                        "thread_id": row[0],
                        "first_message": row[1][:100] + "..." if len(row[1]) > 100 else row[1],
                        "created_at": str(row[2]),
                        "message_count": row[3]
                    })
                
                # Sort by created_at descending (most recent first)
                threads.sort(key=lambda x: x["created_at"], reverse=True)
                
            conn.close()
        except Exception as e:
            logger.error(f"Error getting threads: {e}")
            if conn:
                conn.close()
    
    return jsonify({
        "user_id": user_id,
        "threads": threads[:20]  # Limit to 20 most recent
    })


@app.route('/health')
def health():
    # Test Lakebase connection
    lakebase_status = "unknown"
    try:
        conn = get_lakebase_connection()
        if conn:
            lakebase_status = "connected"
            conn.close()
        else:
            lakebase_status = "fallback_to_memory"
    except Exception as e:
        lakebase_status = f"error: {str(e)[:50]}"
    
    return jsonify({
        "status": "ok",
        "memory_enabled": True,
        "lakebase_status": lakebase_status,
        "lakebase_instance": LAKEBASE_INSTANCE_NAME,
        "dist_exists": os.path.exists(DIST_DIR)
    })


@app.route('/<path:path>')
def serve_static(path):
    file_path = os.path.join(DIST_DIR, path)
    if os.path.exists(file_path):
        return send_from_directory(DIST_DIR, path)
    return send_from_directory(DIST_DIR, 'index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8000)), debug=True)
