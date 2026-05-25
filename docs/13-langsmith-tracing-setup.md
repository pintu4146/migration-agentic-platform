# LangSmith Tracing Setup for LangGraph

## Overview

This document provides comprehensive guidance on setting up LangSmith tracing for LangGraph workflows in the migration copilot POC. LangSmith provides automatic tracing for all LangGraph operations, including state transitions, node executions, and LLM calls.

## Why LangSmith for LangGraph?

LangSmith is the **official observability platform** for LangChain and LangGraph, providing:

- ✅ **Automatic tracing** of all LangGraph nodes and edges
- ✅ **State transition visualization** across the workflow
- ✅ **LLM call tracking** with prompts, responses, and tokens
- ✅ **Agent decision tracking** with reasoning chains
- ✅ **Human-in-the-loop** interaction logging
- ✅ **Error tracking** with full context
- ✅ **Performance metrics** for each node
- ✅ **Zero code changes** required for basic tracing

## Basic Setup

### 1. Environment Variables

The simplest way to enable LangSmith tracing is through environment variables:

```python
import os

# Enable LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "migration-copilot-poc"
os.environ["LANGCHAIN_API_KEY"] = "your-langsmith-api-key"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"  # Optional, this is default
```

**Important**: Set these environment variables **before** importing LangGraph or LangChain modules.

### 2. Configuration File

For production, use a configuration file:

```python
# backend/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # LangSmith Settings
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str = "migration-copilot-poc"
    LANGSMITH_TRACING: bool = True
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    
    class Config:
        env_file = ".env"

settings = Settings()

# Apply settings
if settings.LANGSMITH_TRACING:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
    os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGSMITH_ENDPOINT
```

### 3. Environment File

```bash
# .env
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_PROJECT=migration-copilot-poc
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

## Automatic Tracing

Once environment variables are set, **all LangGraph operations are automatically traced**:

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

# Define state
class MigrationState(TypedDict):
    project_id: str
    phase: str
    data: dict

# Create workflow
workflow = StateGraph(MigrationState)

# Add nodes
async def context_retrieval_node(state: MigrationState) -> MigrationState:
    # This node execution is automatically traced
    result = await fetch_context()
    return {"data": result, "phase": "extraction"}

workflow.add_node("context_retrieval", context_retrieval_node)
workflow.set_entry_point("context_retrieval")

# Compile and run
graph = workflow.compile()
result = await graph.ainvoke({"project_id": "123", "phase": "init"})

# All of the above is automatically traced to LangSmith!
```

## What Gets Traced Automatically

### 1. Workflow Execution

- Workflow start and end
- Total execution time
- Final state
- Configuration used

### 2. Node Executions

- Node name
- Input state
- Output state
- Execution time
- Success/failure status

### 3. State Transitions

- Previous state
- New state
- State diff
- Transition timestamp

### 4. LLM Calls

- Model used
- Prompt (system + user)
- Response
- Token usage (prompt, completion, total)
- Latency
- Cost estimate

### 5. Errors

- Error type
- Error message
- Stack trace
- State at time of error

## Custom Tracing

For additional context, use the `@traceable` decorator:

```python
from langsmith import traceable

@traceable(name="extract_technical_facts")
async def extract_facts(docs: list) -> dict:
    """Custom traced function"""
    # Extract facts from documents
    facts = await llm.invoke(prompt)
    return facts

# Usage in node
async def extraction_node(state: MigrationState) -> MigrationState:
    docs = state["normalized_docs"]
    
    # This call is traced with custom name
    facts = await extract_facts(docs)
    
    return {
        "extracted_facts": facts,
        "phase": "questionnaire"
    }
```

### Adding Metadata

Add custom metadata to traces:

```python
from langsmith import traceable

@traceable(
    name="state_commit",
    metadata={
        "operation": "state_update",
        "critical": True
    }
)
async def commit_state_patch(
    patch: dict,
    expected_version: int,
    committed_by: str
) -> dict:
    """Traced state commit with metadata"""
    # Commit logic
    return updated_state
```

### Tagging Traces

Add tags for filtering:

```python
from langsmith import traceable

@traceable(
    name="llm_call",
    tags=["extraction", "gpt-4", "high-cost"]
)
async def call_llm(prompt: str) -> str:
    response = await llm.invoke(prompt)
    return response
```

## Tracing State Transitions

Track state changes explicitly:

```python
from langsmith import traceable
from datetime import datetime

class StateManager:
    def __init__(self):
        self._state = None
    
    @traceable(name="state_transition")
    async def commit_state_patch(
        self,
        patch: dict,
        expected_version: int,
        committed_by: str
    ) -> dict:
        """Traced state commit"""
        # Version check
        if self._state["state_version"] != expected_version:
            raise StateTransactionError("Version mismatch")
        
        # Record transition
        transition = {
            "from_version": expected_version,
            "to_version": expected_version + 1,
            "from_phase": self._state["phase"],
            "to_phase": patch.get("phase", self._state["phase"]),
            "committed_by": committed_by,
            "timestamp": datetime.utcnow().isoformat(),
            "patch": patch
        }
        
        # Apply patch
        for key, value in patch.items():
            self._state[key] = value
        
        self._state["state_version"] += 1
        
        return self._state
```

## Tracing Agent Decisions

Track agent reasoning:

```python
from langsmith import traceable

class ExtractionAgent:
    @traceable(name="extraction_agent_execute")
    async def execute(self, state: dict) -> dict:
        """Traced agent execution"""
        docs = state["normalized_docs"]
        
        # Trace extraction
        facts = await self._extract_facts(docs)
        
        # Trace confidence calculation
        confidence = await self._calculate_confidence(facts, docs)
        
        return {
            "extracted_facts": facts,
            "confidence_scores": confidence,
            "phase": "questionnaire"
        }
    
    @traceable(name="extract_facts")
    async def _extract_facts(self, docs: list) -> dict:
        """Traced fact extraction"""
        prompt = self._build_prompt(docs)
        response = await self.llm.invoke(prompt)
        return response
    
    @traceable(name="calculate_confidence")
    async def _calculate_confidence(self, facts: dict, docs: list) -> dict:
        """Traced confidence calculation"""
        # Calculate confidence scores
        return confidence_scores
```

## Viewing Traces

### LangSmith Dashboard

Access traces at: https://smith.langchain.com

**Project View:**
- All workflow runs
- Success/failure rates
- Average execution time
- Cost tracking

**Run Details:**
- Complete execution tree
- Node-by-node breakdown
- State at each step
- LLM calls with prompts/responses
- Error details

**Filtering:**
- By project
- By tags
- By date range
- By status (success/error)
- By metadata

### Trace Structure

```
Run: workflow_project-123
├── Node: supervisor
│   ├── Input: {project_id: "123", phase: "init"}
│   ├── Output: {phase: "context_retrieval"}
│   └── Duration: 5ms
├── Node: context_retrieval
│   ├── Input: {project_id: "123", phase: "init"}
│   ├── MCP Request
│   │   ├── Profile: context_retrieval
│   │   ├── Duration: 1.2s
│   │   └── Documents: 15
│   ├── Output: {context_pack: {...}, phase: "extraction"}
│   └── Duration: 1.5s
├── Node: extraction
│   ├── Input: {context_pack: {...}, phase: "extraction"}
│   ├── LLM Call: extract_facts
│   │   ├── Model: gpt-4-turbo
│   │   ├── Prompt: "Extract technical facts..."
│   │   ├── Response: {...}
│   │   ├── Tokens: 1500 prompt, 800 completion
│   │   ├── Cost: $0.045
│   │   └── Duration: 3.2s
│   ├── Output: {extracted_facts: {...}, phase: "questionnaire"}
│   └── Duration: 3.5s
└── ...
```

## Integration with Workflow

### Complete Setup Example

```python
# backend/app/main.py
import os
from fastapi import FastAPI
from app.config import settings

# Setup LangSmith tracing
if settings.LANGSMITH_TRACING:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY

# Import after setting environment variables
from langgraph.graph import StateGraph, END
from app.orchestration.workflow import MigrationWorkflow

app = FastAPI()

# Create workflow (automatically traced)
workflow = MigrationWorkflow()

@app.post("/workflows/{project_id}/start")
async def start_workflow(project_id: str):
    """Start migration workflow (traced)"""
    initial_state = {
        "project_id": project_id,
        "phase": "init",
        "state_version": 0
    }
    
    config = {"configurable": {"thread_id": project_id}}
    
    # This entire workflow execution is traced
    result = await workflow.graph.ainvoke(initial_state, config)
    
    return {"status": "started", "project_id": project_id}
```

## Tracing Human-in-the-Loop

Track human review interactions:

```python
from langsmith import traceable

@traceable(name="human_review_gate")
async def human_review_gate_node(state: dict) -> dict:
    """Traced human review gate"""
    # Workflow pauses here
    # Human reviews intake draft
    # This pause is tracked in LangSmith
    return state

@traceable(name="human_review_approval")
async def approve_intake(project_id: str, comments: list) -> dict:
    """Traced human approval"""
    # Get current state
    state = await state_manager.read_state()
    
    # Update with human feedback
    patch = {
        "human_reviewed": True,
        "review_comments": comments,
        "review_timestamp": datetime.utcnow().isoformat()
    }
    
    # Commit (traced)
    updated_state = await state_manager.commit_state_patch(
        patch,
        state["state_version"],
        "human_reviewer"
    )
    
    return updated_state
```

## Error Tracking

Errors are automatically captured with full context:

```python
async def extraction_node(state: dict) -> dict:
    try:
        # Attempt extraction
        facts = await extract_facts(state["docs"])
        return {"extracted_facts": facts}
    except Exception as e:
        # Error is automatically traced with:
        # - Error type
        # - Error message
        # - Stack trace
        # - State at time of error
        # - Node name
        raise
```

## Performance Monitoring

### Trace Metrics

LangSmith automatically tracks:

- **Latency**: Time for each node and LLM call
- **Token Usage**: Prompt, completion, and total tokens
- **Cost**: Estimated cost per LLM call
- **Success Rate**: Percentage of successful runs
- **Error Rate**: Percentage of failed runs

### Custom Metrics

Add custom metrics to traces:

```python
from langsmith import traceable
import time

@traceable(name="process_documents")
async def process_documents(docs: list) -> dict:
    start_time = time.time()
    
    # Process documents
    result = await process(docs)
    
    # Add custom metrics
    duration = time.time() - start_time
    
    # Metrics are automatically included in trace
    return {
        "result": result,
        "metrics": {
            "duration_seconds": duration,
            "documents_processed": len(docs),
            "throughput": len(docs) / duration
        }
    }
```

## Best Practices

### 1. Use Descriptive Names

```python
# Good: Descriptive names
@traceable(name="extract_technical_stack_from_confluence")
async def extract_stack(docs):
    pass

# Avoid: Generic names
@traceable(name="process")
async def process(data):
    pass
```

### 2. Add Meaningful Metadata

```python
@traceable(
    name="llm_call",
    metadata={
        "model": "gpt-4-turbo",
        "purpose": "fact_extraction",
        "cost_tier": "high",
        "criticality": "high"
    }
)
async def call_llm(prompt):
    pass
```

### 3. Use Tags for Filtering

```python
@traceable(
    name="extraction",
    tags=["agent:extraction", "model:gpt-4", "phase:analysis"]
)
async def extract(docs):
    pass
```

### 4. Trace Critical Operations

Always trace:
- State transitions
- LLM calls
- Agent decisions
- Human interactions
- Error-prone operations

### 5. Don't Over-Trace

Avoid tracing:
- Simple utility functions
- Pure data transformations
- Frequent low-level operations

## Troubleshooting

### Traces Not Appearing

**Problem**: Traces not showing in LangSmith dashboard

**Solutions**:

1. **Check API Key**:
```python
import os
print(os.environ.get("LANGCHAIN_API_KEY"))
# Should print: lsv2_pt_...
```

2. **Verify Tracing Enabled**:
```python
print(os.environ.get("LANGCHAIN_TRACING_V2"))
# Should print: true
```

3. **Check Project Name**:
```python
print(os.environ.get("LANGCHAIN_PROJECT"))
# Should print: migration-copilot-poc
```

4. **Test Connection**:
```python
from langsmith import Client

client = Client()
try:
    client.list_projects()
    print("✅ Connected to LangSmith")
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

### Slow Tracing

**Problem**: Tracing adds latency

**Solutions**:

1. **Async Tracing** (default in LangSmith):
```python
# Traces are sent asynchronously by default
# No action needed
```

2. **Batch Tracing**:
```python
# LangSmith batches traces automatically
# Adjust batch size if needed (advanced)
```

3. **Sampling** (for high-volume production):
```python
import random

def should_trace():
    return random.random() < 0.1  # 10% sampling

if should_trace():
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
```

### Missing LLM Calls

**Problem**: LLM calls not traced

**Solution**: Ensure using LangChain LLM wrappers:

```python
# Good: LangChain wrapper (auto-traced)
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4-turbo")
response = await llm.ainvoke(prompt)  # Traced

# Avoid: Direct OpenAI client (not traced)
from openai import AsyncOpenAI

client = AsyncOpenAI()
response = await client.chat.completions.create(...)  # Not traced
```

## Cost Tracking

LangSmith automatically estimates costs:

```python
# View in dashboard:
# - Cost per run
# - Cost per node
# - Cost per LLM call
# - Total project cost
# - Cost trends over time
```

### Cost Optimization

Use traces to identify expensive operations:

1. **Find High-Cost Nodes**:
   - Sort runs by cost
   - Identify expensive LLM calls
   - Optimize prompts

2. **Reduce Token Usage**:
   - Shorter prompts
   - Structured output (JSON mode)
   - Caching responses

3. **Use Cheaper Models**:
   - GPT-3.5 for simple tasks
   - Gemini for fallback
   - Cache expensive calls

## Summary

### Setup Checklist

- [ ] Set `LANGCHAIN_TRACING_V2=true`
- [ ] Set `LANGCHAIN_PROJECT=migration-copilot-poc`
- [ ] Set `LANGCHAIN_API_KEY=your-key`
- [ ] Set environment variables before imports
- [ ] Verify traces appear in dashboard
- [ ] Add custom traces for critical operations
- [ ] Add metadata and tags for filtering
- [ ] Monitor costs and performance

### Key Benefits

✅ **Zero-config tracing** for LangGraph workflows
✅ **Complete visibility** into agent decisions
✅ **State transition tracking** for debugging
✅ **LLM call monitoring** with costs
✅ **Error tracking** with full context
✅ **Performance metrics** for optimization
✅ **Human interaction logging** for audit trails

LangSmith tracing is **essential** for debugging, monitoring, and optimizing the migration copilot POC!