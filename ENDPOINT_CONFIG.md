# Agent Endpoint Configuration Guide

This document lists all files that need to be updated when changing the agent serving endpoint.

---

## Agent Serving Endpoint

The agent serving endpoint (`mas-8f9f5609-endpoint`) is referenced in **4 files**:

### 1. `app.py` (line 28)

```python
SERVING_ENDPOINT = os.getenv("SERVING_ENDPOINT", "mas-8f9f5609-endpoint")
```

### 2. `deploy/app.py` (line 28)

```python
SERVING_ENDPOINT = os.getenv("SERVING_ENDPOINT", "mas-8f9f5609-endpoint")
```

### 3. `app.yaml` (lines 12, 18-19)

```yaml
env:
  - name: SERVING_ENDPOINT
    value: "mas-8f9f5609-endpoint"

permissions:
  serving_endpoints:
    - name: mas-8f9f5609-endpoint
```

### 4. `deploy/app.yaml` (lines 12, 18-19)

```yaml
env:
  - name: SERVING_ENDPOINT
    value: "mas-8f9f5609-endpoint"

permissions:
  serving_endpoints:
    - name: mas-8f9f5609-endpoint
```

---

## LLM Foundation Model Endpoint

The LLM endpoint used by the agent is defined in **1 file**:

### `agent_with_memory.py` (line 68)

```python
LLM_ENDPOINT_NAME = "databricks-gpt-oss-120b"
```

Change this if using a different foundation model (e.g., `databricks-claude-sonnet-4`, `databricks-meta-llama-3-3-70b-instruct`).

---

## Quick Reference

| File | Line | Variable | Current Value |
|------|------|----------|---------------|
| `app.py` | 28 | `SERVING_ENDPOINT` | `mas-8f9f5609-endpoint` |
| `deploy/app.py` | 28 | `SERVING_ENDPOINT` | `mas-8f9f5609-endpoint` |
| `app.yaml` | 12, 19 | `SERVING_ENDPOINT` | `mas-8f9f5609-endpoint` |
| `deploy/app.yaml` | 12, 19 | `SERVING_ENDPOINT` | `mas-8f9f5609-endpoint` |
| `agent_with_memory.py` | 68 | `LLM_ENDPOINT_NAME` | `databricks-gpt-oss-120b` |

---

## Steps to Update

1. Replace the endpoint name in all 4 files listed above
2. Update the LLM endpoint if using a different model
3. Redeploy the Databricks App
4. Verify the app connects to the new endpoint
