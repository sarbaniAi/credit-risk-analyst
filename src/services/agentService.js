/**
 * Agent Service with Memory Support
 * Handles communication with the Credit Risk Agent endpoint + memory APIs
 */

const AGENT_ENDPOINT = '/api/serving-endpoints/mas-8f9f5609-endpoint/invocations';
const MEMORY_API = '/api/memory';
const TOKEN_KEY = 'databricks_pat_token';
const USER_ID_KEY = 'databricks_user_id';

// Session/thread management
export const generateThreadId = () => {
  return `thread-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
};

// Token management
export const saveToken = (token) => {
  if (token && token.trim()) {
    localStorage.setItem(TOKEN_KEY, token.trim());
    console.log('[AgentService] Token saved');
    return true;
  }
  return false;
};

export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const hasToken = () => !!localStorage.getItem(TOKEN_KEY);
export const clearToken = () => {
  localStorage.removeItem(TOKEN_KEY);
  console.log('[AgentService] Token cleared');
};

// User ID management (for memory)
export const saveUserId = (userId) => {
  if (userId && userId.trim()) {
    localStorage.setItem(USER_ID_KEY, userId.trim());
    console.log('[AgentService] User ID saved:', userId);
    return true;
  }
  return false;
};

export const getUserId = () => localStorage.getItem(USER_ID_KEY) || 'default_user';
export const hasUserId = () => !!localStorage.getItem(USER_ID_KEY);
export const clearUserId = () => localStorage.removeItem(USER_ID_KEY);

const MAX_MCP_ITERATIONS = 5;

/**
 * Build MCP approval response for a request
 * Format: { type: "mcp_approval_response", id: "...", approval_request_id: "...", approve: true }
 */
const buildMcpApprovalResponse = (mcpRequest) => {
  return {
    type: 'mcp_approval_response',
    id: mcpRequest.id,
    approval_request_id: mcpRequest.id,
    approve: true
  };
};

/**
 * Extract MCP approval requests from the response output
 */
const extractMcpApprovalRequests = (output) => {
  if (!output || !Array.isArray(output)) return [];
  return output.filter(item => item.type === 'mcp_approval_request');
};

/**
 * Make a raw API call to the agent endpoint
 */
const makeAgentRequest = async (payload, token) => {
  const response = await fetch(AGENT_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      'X-Databricks-Token': token
    },
    body: JSON.stringify(payload)
  });

  console.log('[AgentService] Response status:', response.status);

  const responseText = await response.text();
  console.log('[AgentService] Response length:', responseText.length);

  if (!response.ok) {
    console.error('[AgentService] Error response:', responseText.substring(0, 200));
    throw new Error(`Request failed (${response.status}): ${responseText.substring(0, 200)}`);
  }

  if (!responseText || responseText.length === 0) {
    return { output: [] };
  }

  try {
    return JSON.parse(responseText);
  } catch (parseError) {
    console.error('[AgentService] JSON parse error');
    throw new Error('Invalid JSON response from server');
  }
};

/**
 * Call the Credit Risk Agent with memory context
 * Handles MCP approval requests automatically using the correct chained input format
 */
export const callAgent = async (messages, threadId, userId = null) => {
  const token = getToken();
  const effectiveUserId = userId || getUserId();

  if (!token) {
    throw new Error('No authentication token. Please configure your Databricks token in Settings.');
  }

  // Filter out error messages
  const cleanMessages = messages.filter(msg => 
    !(msg.role === 'assistant' && msg.content?.includes('Error:'))
  );

  console.log('[AgentService] Calling agent with memory context');
  console.log('[AgentService] Thread ID:', threadId);
  console.log('[AgentService] User ID:', effectiveUserId);
  console.log('[AgentService] Messages:', cleanMessages.length);

  // Build initial input
  let currentInput = cleanMessages.map(msg => ({
    role: msg.role,
    content: msg.content
  }));

  let iteration = 0;
  let finalResponse = null;

  // MCP approval loop - keep processing until no more approval requests
  while (iteration < MAX_MCP_ITERATIONS) {
    iteration++;

    const payload = {
      input: currentInput,
      custom_inputs: {
        thread_id: threadId,
        user_id: effectiveUserId
      },
      _auth_token: token
    };

    console.log(`[AgentService] Request iteration ${iteration}, input items:`, currentInput.length);

    const data = await makeAgentRequest(payload, token);
    console.log('[AgentService] Response output items:', data.output?.length || 0);

    // Check for MCP approval requests in the output
    const mcpRequests = extractMcpApprovalRequests(data.output);

    if (mcpRequests.length === 0) {
      // No more approval requests - we're done!
      console.log('[AgentService] ✅ No MCP approval requests - processing complete');
      finalResponse = data;
      break;
    }

    // Found MCP approval requests - auto-approve them
    console.log(`[AgentService] 🔄 Found ${mcpRequests.length} MCP approval request(s)`);

    for (const req of mcpRequests) {
      console.log(`[AgentService] Auto-approving: ${req.name} (id: ${req.id})`);
      try {
        const args = JSON.parse(req.arguments);
        console.log('[AgentService] Tool arguments:', args);
      } catch {}
    }

    // Build new input chain with the output and approval responses
    // Format: [...original input, ...output items, ...approval responses]
    const approvalResponses = mcpRequests.map(buildMcpApprovalResponse);

    currentInput = [
      ...currentInput,
      ...data.output,
      ...approvalResponses
    ];

    console.log('[AgentService] Sending approval, new input length:', currentInput.length);
  }

  if (!finalResponse) {
    console.log('[AgentService] ⚠️ Max iterations reached');
    finalResponse = { output: [] };
  }

  return parseAgentResponse(finalResponse);
};

/**
 * Parse agent response - extract content from messages, tool outputs, and MCP results
 */
const parseAgentResponse = (response) => {
  let content = '';

  console.log('[AgentService] Parsing response, output items:', response.output?.length || 0);

  if (response.output && Array.isArray(response.output)) {
    for (const item of response.output) {
      // Handle regular messages
      if (item.type === 'message' && item.content) {
        if (Array.isArray(item.content)) {
          for (const c of item.content) {
            if (c.type === 'output_text' || c.type === 'text') {
              content += (c.text || '') + '\n\n';
            }
          }
        } else if (typeof item.content === 'string') {
          content += item.content + '\n\n';
        }
      }

      // Log function calls
      if (item.type === 'function_call' && item.name) {
        console.log('[AgentService] Function call:', item.name);
      }

      // Handle MCP tool execution results (Tavily search results)
      if (item.type === 'mcp_call' && item.name) {
        console.log('[AgentService] ✅ MCP tool executed:', item.name);
        if (item.output) {
          try {
            const mcpOutput = JSON.parse(item.output);
            if (mcpOutput.results) {
              content += `\n**Web Search Results:**\n`;
              mcpOutput.results.forEach((result, i) => {
                content += `${i + 1}. **${result.title || 'Result'}**\n`;
                if (result.url) content += `   URL: ${result.url}\n`;
                if (result.content) content += `   ${result.content.substring(0, 300)}...\n\n`;
              });
            } else {
              content += item.output + '\n\n';
            }
          } catch {
            content += item.output + '\n\n';
          }
        }
      }

      // Handle function call outputs
      if (item.type === 'function_call_output' && item.output) {
        console.log('[AgentService] Function output for:', item.name || 'unknown');
        try {
          const output = JSON.parse(item.output);
          if (output.text) {
            content += output.text + '\n\n';
          } else if (output.error) {
            console.log('[AgentService] Tool error:', output.error);
          }
        } catch {
          if (typeof item.output === 'string' && item.output.length < 2000) {
            content += item.output + '\n\n';
          }
        }
      }
    }
  }

  // Fallbacks
  if (!content && response.choices?.[0]?.message?.content) {
    content = response.choices[0].message.content;
  }
  if (!content && response.content) {
    content = response.content;
  }

  const result = content.trim() || 'No response content.';
  console.log('[AgentService] Final content length:', result.length);

  // Extract memory context from response if available
  const memoryInfo = response.custom_outputs || {};

  return {
    content: result,
    raw: response,
    threadId: memoryInfo.thread_id,
    userId: memoryInfo.user_id,
    memoryEnabled: memoryInfo.memory_enabled
  };
};

/**
 * Memory API functions
 */
export const getUserMemories = async (userId = null) => {
  const token = getToken();
  const effectiveUserId = userId || getUserId();

  if (!token) {
    throw new Error('No authentication token');
  }

  const response = await fetch(`${MEMORY_API}/user/${encodeURIComponent(effectiveUserId)}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'X-Databricks-Token': token
    }
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Failed to get memories: ${text}`);
  }

  return response.json();
};

export const clearUserMemories = async (userId = null) => {
  const token = getToken();
  const effectiveUserId = userId || getUserId();

  if (!token) {
    throw new Error('No authentication token');
  }

  const response = await fetch(`${MEMORY_API}/user/${encodeURIComponent(effectiveUserId)}/clear`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'X-Databricks-Token': token
    }
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Failed to clear memories: ${text}`);
  }

  return response.json();
};

export const getThreadHistory = async (threadId) => {
  const token = getToken();

  if (!token) {
    throw new Error('No authentication token');
  }

  const response = await fetch(`${MEMORY_API}/thread/${encodeURIComponent(threadId)}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'X-Databricks-Token': token
    }
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Failed to get thread history: ${text}`);
  }

  return response.json();
};

export const getUserThreads = async (userId = null) => {
  const token = getToken();
  const effectiveUserId = userId || getUserId();

  if (!token) {
    throw new Error('No authentication token');
  }

  const response = await fetch(`${MEMORY_API}/user/${encodeURIComponent(effectiveUserId)}/threads`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'X-Databricks-Token': token
    }
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Failed to get user threads: ${text}`);
  }

  return response.json();
};

export default {
  callAgent,
  generateThreadId,
  saveToken,
  getToken,
  hasToken,
  clearToken,
  saveUserId,
  getUserId,
  hasUserId,
  clearUserId,
  getUserMemories,
  clearUserMemories,
  getThreadHistory,
  getUserThreads
};
