---
name: langgraph
description: LangGraph best practices for building stateful, multi-agent workflows with supervisor patterns, transactional state management, and human-in-the-loop capabilities. Use when building complex agent orchestration systems with LangGraph. Keeps code aligned with LangGraph patterns and best practices.
---

# LangGraph

Official LangGraph skill for building stateful, multi-agent workflows with best practices for state management, agent orchestration, and human-in-the-loop patterns.

## Core Concepts

### StateGraph

Use `StateGraph` for building workflows with typed state:

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class WorkflowState(TypedDict):
    project_id: str
    state_version: int
    phase: str
    data: dict

workflow = StateGraph(WorkflowState)
```

### Nodes

Add nodes as async functions that receive and return state:

```python
async def process_node(state: WorkflowState) -> WorkflowState:
    """Node function that processes state"""
    # Read current state
    current_phase = state["phase"]
    
    # Process
    result = await some_processing(state["data"])
    
    # Return state patch (not full state)
    return {
        "phase": "next_phase",
        "data": result
    }

workflow.add_node("process", process_node)
```

**Important**: Nodes should return state patches, not full state objects, for efficient updates.

### Edges

Add edges to define workflow transitions:

```python
# Simple edge
workflow.add_edge("node_a", "node_b")

# Conditional edge
workflow.add_conditional_edges(
    "supervisor",
    route_function,
    {
        "option_a": "node_a",
        "option_b": "node_b",
        "end": END
    }
)
```

### Entry Point

Set the workflow entry point:

```python
workflow.set_entry_point("supervisor")
```

## Supervisor Pattern

Use supervisor pattern for orchestrating multiple agents:

```python
from langgraph.graph import StateGraph, END
from typing import Literal

class MigrationState(TypedDict):
    phase: str
    data: dict
    error: str | None

workflow = StateGraph(MigrationState)

# Add supervisor node
workflow.add_node("supervisor", supervisor_node)

# Add agent nodes
workflow.add_node("agent_a", agent_a_node)
workflow.add_node("agent_b", agent_b_node)

# Set entry point to supervisor
workflow.set_entry_point("supervisor")

# Supervisor routes to agents
workflow.add_conditional_edges(
    "supervisor",
    route_next_agent,
    {
        "agent_a": "agent_a",
        "agent_b": "agent_b",
        "end": END
    }
)

# Agents return to supervisor
workflow.add_edge("agent_a", "supervisor")
workflow.add_edge("agent_b", "supervisor")
```

### Routing Function

Implement deterministic routing logic:

```python
def route_next_agent(state: MigrationState) -> Literal["agent_a", "agent_b", "end"]:
    """Route based on current phase"""
    phase = state["phase"]
    
    if phase == "init":
        return "agent_a"
    elif phase == "processing":
        return "agent_b"
    else:
        return "end"
```

**Important**: Keep routing logic deterministic and simple. Avoid LLM-based routing for predictable workflows.

## Transactional State Management

### Optimistic Locking

Implement version-based optimistic locking for concurrent safety:

```python
from typing import Dict, Any
import asyncio

class StateManager:
    def __init__(self):
        self._state: Optional[WorkflowState] = None
        self._lock = asyncio.Lock()
    
    async def commit_state_patch(
        self,
        patch: Dict[str, Any],
        expected_version: int,
        committed_by: str
    ) -> WorkflowState:
        """Commit state patch with version check"""
        async with self._lock:
            # Version check (optimistic locking)
            if self._state["state_version"] != expected_version:
                raise StateTransactionError(
                    f"Version mismatch: expected {expected_version}, "
                    f"current {self._state['state_version']}"
                )
            
            # Apply patch
            for key, value in patch.items():
                self._state[key] = value
            
            # Increment version
            self._state["state_version"] += 1
            
            # Record changelog
            self._state["changelog"].append({
                "version": expected_version,
                "patch": patch,
                "committed_by": committed_by,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return deepcopy(self._state)
```

### State Changelog

Maintain write-ahead log for state changes:

```python
class WorkflowState(TypedDict):
    state_version: int
    changelog: List[Dict[str, Any]]
    # ... other fields

# Each state update appends to changelog
changelog_entry = {
    "version": current_version,
    "patch": patch,
    "committed_by": agent_name,
    "timestamp": datetime.utcnow().isoformat()
}
```

## Checkpointing

Use checkpointing for workflow recovery:

```python
from langgraph.checkpoint.memory import MemorySaver

# Add checkpointer
memory = MemorySaver()
graph = workflow.compile(checkpointer=memory)

# Run with checkpoint config
config = {"configurable": {"thread_id": "project-123"}}
result = await graph.ainvoke(initial_state, config)
```

### Checkpoint Recovery

Resume from checkpoint after failure:

```python
# Get checkpoint
checkpoint = await graph.aget_state(config)

# Resume from checkpoint
result = await graph.ainvoke(checkpoint.values, config)
```

## Human-in-the-Loop

### Interrupt Pattern

Use interrupt for human review gates:

```python
from langgraph.graph import StateGraph

workflow = StateGraph(WorkflowState)

# Add human review gate
workflow.add_node("human_review_gate", human_review_node)

# Compile with interrupt
graph = workflow.compile(
    checkpointer=memory,
    interrupt_before=["human_review_gate"]  # Pause before this node
)

# Workflow pauses at human_review_gate
result = await graph.ainvoke(initial_state, config)

# Human reviews and approves
# Resume workflow
result = await graph.ainvoke(None, config)
```

### Update State During Pause

Update state while workflow is paused:

```python
# Get current state
state = await graph.aget_state(config)

# Update state (e.g., add human feedback)
updated_state = {
    **state.values,
    "human_reviewed": True,
    "review_comments": ["Looks good", "Approve"]
}

# Update and resume
await graph.aupdate_state(config, updated_state)
result = await graph.ainvoke(None, config)
```

## Error Handling

### Retry Pattern

Implement retry logic with error tracking:

```python
class WorkflowState(TypedDict):
    retry_count: int
    max_retries: int
    last_error: str | None
    error_log: List[Dict[str, Any]]

async def agent_node(state: WorkflowState) -> WorkflowState:
    try:
        result = await process()
        return {"data": result}
    except Exception as e:
        return {
            "last_error": str(e),
            "error_log": state["error_log"] + [{
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }]
        }

def route_after_error(state: WorkflowState) -> str:
    if state["retry_count"] < state["max_retries"]:
        return "retry"
    else:
        return "end"
```

## Sub-Agents

### Creating Sub-Agents

Define specialized agents as separate nodes:

```python
class ExtractionAgent:
    def __init__(self, llm, tracer):
        self.llm = llm
        self.tracer = tracer
    
    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """Execute extraction logic"""
        # Read state
        docs = state["normalized_docs"]
        
        # Process with LLM
        result = await self.llm.invoke(prompt)
        
        # Return state patch
        return {
            "extracted_facts": result,
            "phase": "questionnaire"
        }

# Add as node
extraction_agent = ExtractionAgent(llm, tracer)
workflow.add_node("extraction", extraction_agent.execute)
```

### Agent Communication

Agents communicate through shared state only:

```python
# Agent A writes to state
async def agent_a(state: WorkflowState) -> WorkflowState:
    result = await process()
    return {"agent_a_output": result}

# Agent B reads from state
async def agent_b(state: WorkflowState) -> WorkflowState:
    input_data = state["agent_a_output"]
    result = await process(input_data)
    return {"agent_b_output": result}
```

**Important**: Agents should NOT communicate directly. All communication goes through shared state.

## Tracing Integration

### LangSmith Tracing

Enable automatic tracing:

```python
import os

# Enable LangSmith tracing
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "my-project"
os.environ["LANGCHAIN_API_KEY"] = "your-api-key"

# All LangGraph operations are automatically traced
```

### Custom Tracing

Add custom traces for state transitions:

```python
from langsmith import traceable

@traceable(name="state_transition")
async def commit_state(patch, version, agent):
    """Traced state commit"""
    return await state_manager.commit_state_patch(
        patch, version, agent
    )
```

## Best Practices

### 1. State Design

Keep state flat and typed:

```python
# Good: Flat, typed state
class WorkflowState(TypedDict):
    project_id: str
    phase: str
    data: dict
    error: str | None

# Avoid: Nested, untyped state
class BadState(TypedDict):
    nested: dict  # Avoid deep nesting
    data: Any     # Avoid Any type
```

### 2. Node Responsibilities

Each node should have a single responsibility:

```python
# Good: Single responsibility
async def extract_facts(state):
    """Only extracts facts"""
    facts = await extract(state["docs"])
    return {"facts": facts}

# Avoid: Multiple responsibilities
async def extract_and_validate(state):
    """Does too much"""
    facts = await extract(state["docs"])
    validated = await validate(facts)
    questions = await generate_questions(validated)
    return {"facts": facts, "validated": validated, "questions": questions}
```

### 3. State Patches

Return minimal state patches:

```python
# Good: Minimal patch
async def process_node(state):
    result = await process()
    return {"result": result}  # Only changed fields

# Avoid: Full state return
async def process_node(state):
    result = await process()
    return {**state, "result": result}  # Unnecessary copy
```

### 4. Error Handling

Always handle errors gracefully:

```python
async def agent_node(state):
    try:
        result = await process()
        return {"data": result, "error": None}
    except Exception as e:
        logger.error(f"Agent failed: {e}")
        return {
            "error": str(e),
            "phase": "error"
        }
```

### 5. Deterministic Routing

Keep routing logic simple and deterministic:

```python
# Good: Simple, deterministic
def route(state):
    if state["phase"] == "init":
        return "process"
    elif state["phase"] == "process":
        return "validate"
    else:
        return "end"

# Avoid: LLM-based routing (non-deterministic, expensive)
async def route(state):
    decision = await llm.invoke("What should we do next?")
    return decision
```

### 6. Async/Await

Use async/await consistently:

```python
# Good: Async throughout
async def agent_node(state):
    result = await async_process()
    return {"result": result}

# Avoid: Mixing sync and async
async def agent_node(state):
    result = sync_process()  # Blocks event loop
    return {"result": result}
```

## Common Patterns

### Parallel Execution

Execute multiple agents in parallel:

```python
from langgraph.graph import StateGraph

workflow = StateGraph(WorkflowState)

# Add parallel nodes
workflow.add_node("agent_a", agent_a)
workflow.add_node("agent_b", agent_b)
workflow.add_node("merge", merge_results)

# Fan-out
workflow.add_edge("start", "agent_a")
workflow.add_edge("start", "agent_b")

# Fan-in
workflow.add_edge("agent_a", "merge")
workflow.add_edge("agent_b", "merge")
```

### Conditional Branching

Branch based on state conditions:

```python
def route_based_on_confidence(state):
    if state["confidence"] > 0.8:
        return "high_confidence_path"
    else:
        return "low_confidence_path"

workflow.add_conditional_edges(
    "analysis",
    route_based_on_confidence,
    {
        "high_confidence_path": "finalize",
        "low_confidence_path": "review"
    }
)
```

### Loop Pattern

Implement loops with conditional exit:

```python
def should_continue(state):
    if state["iteration"] < state["max_iterations"]:
        return "continue"
    else:
        return "end"

workflow.add_node("process", process_node)
workflow.add_conditional_edges(
    "process",
    should_continue,
    {
        "continue": "process",  # Loop back
        "end": END
    }
)
```

## Testing

### Unit Testing Nodes

Test nodes independently:

```python
import pytest

@pytest.mark.asyncio
async def test_extraction_node():
    state = {
        "normalized_docs": [{"content": "test"}],
        "phase": "extraction"
    }
    
    result = await extraction_node(state)
    
    assert "extracted_facts" in result
    assert result["phase"] == "questionnaire"
```

### Integration Testing Workflow

Test complete workflow:

```python
@pytest.mark.asyncio
async def test_workflow():
    initial_state = {
        "project_id": "test-123",
        "phase": "init"
    }
    
    config = {"configurable": {"thread_id": "test"}}
    result = await graph.ainvoke(initial_state, config)
    
    assert result["phase"] == "complete"
```

## Performance Optimization

### Caching

Cache expensive operations:

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def expensive_computation(input_data):
    return process(input_data)

async def agent_node(state):
    result = expensive_computation(state["data"])
    return {"result": result}
```

### Batch Processing

Process multiple items in batches:

```python
async def batch_process_node(state):
    items = state["items"]
    batch_size = 10
    
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        batch_results = await process_batch(batch)
        results.extend(batch_results)
    
    return {"results": results}
```

## Monitoring

### Metrics

Track workflow metrics:

```python
from prometheus_client import Counter, Histogram

workflow_executions = Counter(
    'workflow_executions_total',
    'Total workflow executions',
    ['phase', 'status']
)

node_duration = Histogram(
    'node_duration_seconds',
    'Node execution duration',
    ['node_name']
)

async def monitored_node(state):
    start_time = time.time()
    
    try:
        result = await process()
        workflow_executions.labels(
            phase=state["phase"],
            status="success"
        ).inc()
        return {"result": result}
    finally:
        duration = time.time() - start_time
        node_duration.labels(node_name="process").observe(duration)
```

## Migration Copilot Example

Complete example for migration copilot:

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, List, Dict, Any

class MigrationState(TypedDict):
    project_id: str
    state_version: int
    phase: str
    context_pack: Dict[str, Any] | None
    extracted_facts: Dict[str, Any] | None
    missing_questions: List[Dict[str, Any]]
    intake_draft: Dict[str, Any] | None
    human_reviewed: bool
    migration_plan: Dict[str, Any] | None

# Create workflow
workflow = StateGraph(MigrationState)

# Add nodes
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("context_retrieval", context_retrieval_node)
workflow.add_node("extraction", extraction_node)
workflow.add_node("questionnaire", questionnaire_node)
workflow.add_node("intake_draft", intake_draft_node)
workflow.add_node("human_review_gate", human_review_gate_node)
workflow.add_node("migration_planning", migration_planning_node)

# Set entry point
workflow.set_entry_point("supervisor")

# Add routing
workflow.add_conditional_edges(
    "supervisor",
    route_next_node,
    {
        "context_retrieval": "context_retrieval",
        "extraction": "extraction",
        "questionnaire": "questionnaire",
        "intake_draft": "intake_draft",
        "human_review_gate": "human_review_gate",
        "migration_planning": "migration_planning",
        "end": END
    }
)

# All nodes return to supervisor
for node in ["context_retrieval", "extraction", "questionnaire", 
             "intake_draft", "human_review_gate", "migration_planning"]:
    workflow.add_edge(node, "supervisor")

# Compile with checkpointing and interrupt
memory = MemorySaver()
graph = workflow.compile(
    checkpointer=memory,
    interrupt_before=["human_review_gate"]
)

# Run workflow
config = {"configurable": {"thread_id": "project-123"}}
result = await graph.ainvoke(initial_state, config)
```

## Do Not

### Do not mutate state directly

```python
# DO NOT DO THIS
async def bad_node(state):
    state["data"] = "modified"  # Direct mutation
    return state

# Do this instead
async def good_node(state):
    return {"data": "modified"}  # Return patch
```

### Do not use global state

```python
# DO NOT DO THIS
global_data = {}

async def bad_node(state):
    global_data["key"] = "value"  # Global state
    return state

# Do this instead
async def good_node(state):
    return {"key": "value"}  # Use workflow state
```

### Do not skip error handling

```python
# DO NOT DO THIS
async def bad_node(state):
    result = await risky_operation()  # No error handling
    return {"result": result}

# Do this instead
async def good_node(state):
    try:
        result = await risky_operation()
        return {"result": result, "error": None}
    except Exception as e:
        return {"error": str(e), "phase": "error"}
```

## References

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangSmith Tracing](https://docs.smith.langchain.com/)
- [State Management Patterns](https://langchain-ai.github.io/langgraph/concepts/low_level/)
- [Human-in-the-Loop](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)