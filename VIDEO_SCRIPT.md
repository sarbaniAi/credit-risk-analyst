# Credit Risk Analyst Agent - Video Demo Script

**Duration:** ~5-7 minutes  
**Presenter:** [Your Name]  
**Target Audience:** Data Engineers, ML Engineers, Solution Architects, Developers

---

## 🎬 INTRO (30 seconds)

**[SCREEN: App landing page with "Credit Risk Analyst Agent" header]**

> "Hi everyone! Today I'm excited to show you something we've built using Databricks' newest capabilities - a Credit Risk Analyst Agent with persistent memory.
>
> This agent doesn't just answer questions - it **remembers** your analysis history across sessions, learns customer information over time, and provides personalized insights based on your previous interactions.
>
> Let's dive in!"

---

## 📋 SECTION 1: What We're Using (45 seconds)

**[SCREEN: Architecture diagram or Databricks console]**

> "Before we start the demo, let me quickly cover the key technologies powering this solution:
>
> **First, Agentbricks** - Databricks' framework for building AI agents. Our Credit Risk Analyst is built with Agentbricks, giving it the ability to coordinate multiple specialized tools - from querying customer data to generating credit reports.
>
> **Second, Lakebase** - Databricks' fully-managed PostgreSQL database. This is where the magic happens for memory. Instead of losing context after each conversation, we store memories in Lakebase, making them persistent across sessions.
>
> **Third, Databricks Apps** - We've deployed this as a Databricks App, so it runs entirely within the Databricks ecosystem with built-in security and authentication."

---

## 🎯 SECTION 2: First Interaction - Analyzing a Customer (90 seconds)

**[SCREEN: Fresh chat interface]**

> "."

**[TYPE: "Analyze customer 34997"]**

> "Watch what happens - the agent is calling multiple tools behind the scenes. It's querying our customer database, retrieving finaLet me start with a fresh conversation. I'll ask the agent to analyze a customerncial metrics, and generating a comprehensive credit risk report."

**[SCREEN: Show the response with customer details, risk assessment]**

> "Here's our analysis. Customer 34997 has been assessed as **HIGH RISK** based on their financial profile. The agent shows us their income, credit metrics, and the reasoning behind the risk assessment.
>
> Now here's the interesting part - let me ask for more details."

**[TYPE: "What's their email address?"]**

> "The agent queries the customer_personal_info table and returns the email: **chamelr04@desdev.cn**
>
> Now, this information - the customer ID, risk level, and email - has been automatically **extracted and stored in memory**. Let me show you why that matters."

---

## 🧠 SECTION 3: Memory in Action (90 seconds)

**[SCREEN: Click "New" button to start new thread]**

> "I'm starting a completely **new conversation thread**. In a traditional chatbot, we'd lose all context from the previous chat. But watch this..."

**[TYPE: "What customers have I analyzed?"]**

**[SCREEN: Show response with memory context]**

> "The agent remembers! It tells me I've analyzed customer 34997, shows their HIGH_RISK rating, and even recalls the email address we discovered earlier.
>
> This is **long-term memory** powered by Lakebase. The agent stores key insights - customer IDs, risk assessments, email addresses, financial data - and retrieves them automatically in future conversations."

**[CLICK: Memory button in header]**

> "Let me show you the Memory Panel. Here you can see all the stored memories for your user account:
> - Analyzed customers
> - Risk assessments  
> - Customer emails
> - Financial data like income and credit scores
>
> This memory persists even if you close the browser and come back tomorrow."

---

## 📜 SECTION 4: Conversation History (60 seconds)

**[CLICK: History button]**

> "We also have full **Conversation History**. Click the History button, and you see all your past conversation threads.
>
> This serves two purposes:
> 1. **For users** - you can go back and review previous analyses
> 2. **For compliance** - in financial services, you need audit trails of all AI-assisted decisions
>
> Let me click on a previous thread..."

**[CLICK: On a thread in the history panel]**

> "And it loads the entire conversation right back into the chat. The memory and history work together to give you a complete picture of your interactions."

---

## 🗑️ SECTION 5: Clear Memory - Fresh Start (45 seconds)

**[SCREEN: Point to Clear Memory button]**

> "What if you want to start fresh? Maybe you're beginning a new analysis project or want to reset for a demo.
>
> Click the Clear Memory button..."

**[CLICK: Clear Memory button, show confirmation dialog]**

> "You get a confirmation showing exactly what will be cleared - emails, risk assessments, customer data.
>
> Importantly, the **chat history is preserved** for audit purposes. Only the learned memories are cleared."

**[CLICK: Clear Memory]**

> "Now the agent has a clean slate - it won't remember previous customers until you analyze them again."

---

## 🔍 SECTION 6: Web Search with MCP Auto-Approval (60 seconds)

**[SCREEN: Chat interface]**

> "Now let me show you something cool - the agent can also search the web using Tavily through MCP, the Model Context Protocol.
>
> Let's say I want to verify if a customer's email domain is legitimate."

**[TYPE: "Is infoseek.co.jp a valid domain?"]**

> "Watch the console - you'll see the agent requesting MCP approval for the Tavily search. But instead of prompting you to click approve, our app **automatically approves** these requests.
>
> This is important for enterprise use - we don't want analysts clicking 'approve' for every search. The app handles it seamlessly."

**[SCREEN: Show response with web search results]**

> "And there's the answer - the agent searched the web, found that Infoseek was acquired and discontinued, and warns us this email domain might be problematic.
>
> This combines **internal data** from our credit system with **external validation** - exactly what a real analyst would do."

---

## 🏗️ SECTION 7: Technical Architecture (60 seconds)

**[SCREEN: Show architecture diagram or code snippets]**

> "Let me briefly explain how this works under the hood:
>
> **The Agent** runs on a Databricks Model Serving endpoint - it's stateless by design for scalability.
>
> **The Memory Layer** sits in our Flask backend. When you send a message:
> 1. We retrieve your memories from Lakebase
> 2. Inject them as **concise, silent context** - just key-value pairs
> 3. The agent uses this context but **doesn't repeat it** back to you
> 4. After the response, we extract new memories - customer IDs, emails, risk levels
> 5. Store them back in Lakebase for next time
>
> **For MCP tools**, we auto-approve requests and chain them back into the conversation until the agent completes its workflow.
>
> **The Frontend** is a React app deployed as a Databricks App, with full SSO integration.
>
> The beautiful thing is - this pattern works for **any** agent. You can add persistent memory to your own Agentbricks solutions using this same approach."

---

## 🎉 SECTION 8: Wrap Up (30 seconds)

**[SCREEN: App interface with all features visible]**

> "To summarize what we've built:
>
> ✅ A Credit Risk Analyst Agent using **Agentbricks**  
> ✅ Persistent memory powered by **Lakebase**  
> ✅ **MCP auto-approval** for seamless web searches  
> ✅ **Optimized memory injection** - concise and silent  
> ✅ Deployed as a **Databricks App**  
> ✅ Full conversation history for compliance  
> ✅ Ability to clear memory and start fresh
>
> This pattern - adding external memory to stateless agents with automatic tool approval - opens up so many possibilities for personalized AI assistants in financial services and beyond.
>
> Thanks for watching! Check out the blog post linked below for the full implementation details. See you next time!"

---

## 📝 DEMO FLOW CHECKLIST

Use this checklist during recording:

- [ ] App loads with fresh state
- [ ] Show header: "Credit Risk Analyst Agent - Powered by Agentbricks & Lakebase"
- [ ] Analyze customer 34997 → Show full response
- [ ] Ask for email → Get chamelr04@desdev.cn
- [ ] Click "New" → Start fresh thread
- [ ] Ask "What customers have I analyzed?" → Memory recalls!
- [ ] **NEW**: Ask "What's the email for my customer?" → Direct concise answer (no repetition!)
- [ ] Open Memory Panel → Show stored data
- [ ] Open History Panel → Show past threads
- [ ] Load a previous thread
- [ ] **NEW**: Ask "Is [domain] valid?" → Show MCP auto-approval in console
- [ ] Show Clear Memory confirmation
- [ ] (Optional) Clear and show fresh state

---

## 🎤 KEY TALKING POINTS

If you need to improvise, hit these points:

1. **Memory is external** - Agent stays stateless, memory is in the app layer
2. **Lakebase = PostgreSQL** - Familiar, reliable, fully managed by Databricks
3. **Per-user isolation** - Each user has their own memories
4. **Automatic extraction** - No manual tagging, agent responses are parsed for customer IDs, emails, risk levels
5. **Optimized injection** - Memory is concise and silent; agent doesn't repeat it
6. **MCP auto-approval** - External tools (Tavily) work seamlessly without manual clicks
7. **Compliance-ready** - History preserved for audit
8. **Pattern is reusable** - Works for any Agentbricks agent

---

## 📊 SAMPLE QUESTIONS FOR DEMO

Good questions to ask during demo:

```
# Basic Analysis
"Analyze customer 34997"
"What's their email address?"
"What risk factors contributed to this assessment?"

# Memory Recall (in new thread)
"Which customers have I analyzed?"
"What's my customer's email?" (tests concise memory response)
"Give me the email for customer 34997"

# Web Search with MCP (shows auto-approval)
"Is gmpg.org a valid domain?"
"Is prweb.com legitimate?"
"Verify the email domain for my customer"

# Advanced
"Compare customers 34997 and 93486"
"Give me recommendations for managing high-risk customers"
```

---

*Script prepared for Databricks Credit Risk Analyst Agent Demo*
