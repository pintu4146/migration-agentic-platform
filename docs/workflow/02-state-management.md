# State Management - Deep Dive

## Table of Contents
1. [State Schema](#state-schema)
2. [State Lifecycle](#state-lifecycle)
3. [State Reducers](#state-reducers)
4. [State Versioning](#state-versioning)
5. [State Persistence](#state-persistence)

---

## State Schema

### MigrationState TypedDict

**File**: `backend/app/orchestration/state.py`

```python
from typing import TypedDict, Annotated, List, Dict, Any

class MigrationState(TypedDict):
    # Core Identifiers
    project_id: str                    # Unique project identifier
    state_version: int                 # Increments with each update
    
    # Workflow Control
    phase: str                         # Current workflow phase
    next_node: str                     # Next node to execute
    supervisor_reason: str             # Why supervisor chose this node
    
    # MCP Configuration
    mcp_request_profile: Dict[str, Any]  # MCP retrieval configuration
    
    # Context Data (Phase 2)
    context_pack: Dict[str, Any]       # Raw context from MCP/Qdrant
    normalized_docs: Annotated[List[Dict[str, Any]], merge_lists]
    
    # Extraction Data (Phase 3)
    extracted_facts: Dict[str, Any]    # Structured facts by category
    confidence_scores: Dict[str, float]  # fact_id → confidence
    evidence_map: Dict[str, List[str]]   # fact_id → [doc_ids]
    
    # Questionnaire Data (Phase 4)
    missing_questions: Annotated[List[Dict[str, Any]], merge_lists]
    answered_questions: Annotated[List[Dict[str, Any]], merge_lists]
    question_priorities: Dict[str, float]  # question_id → priority
    gap_analysis: Dict[str, Any]
    
    # Intake Data (Phase 5)
    intake_draft: Dict[str, Any]
    
    # Review Data (Phase 6)
    human_reviewed: bool
    review_comments: Annotated[List[str], merge_lists]
    review_flags: Annotated[List[str], merge_lists]
    
    # Migration Planning Data (Phase 7)
    migration_plan: Dict[str, Any]
    
    # Validation Data (Phase 8)
    validation_results: Dict[str, Any]
    
    # Metadata
    trace_metadata: Dict[str, Any]     # LangSmith tracing data
    state_changelog: Annotated[List[StateChangelogEntry], merge_lists]
    error_log: Annotated[List[Dict[str, Any]], merge_lists]
    last_error: str
    
    # Timestamps
    created_at: str                    # ISO 8601 timestamp
    updated_at: str                    # ISO 8601 timestamp
    last_committed_by: str             # Agent/node name
    last_committed_at: str             # ISO 8601 timestamp
```

### Field Categories

#### 1. Core Identifiers
- **project_id**: Links state to a specific project
- **state_version**: Tracks state evolution (0 → 1 → 2 → ...)

#### 2. Workflow Control
- **phase**: Current phase (init, context_retrieval, extraction, etc.)
- **next_node**: Supervisor's decision for next step
- **supervisor_reason**: Human-readable explanation

#### 3. Data Fields
Each phase adds its own data fields:
- Phase 2: `context_pack`, `normalized_docs`
- Phase 3: `extracted_facts`, `confidence_scores`, `evidence_map`
- Phase 4: `missing_questions`, `gap_analysis`
- Phase 5: `intake_draft`
- Phase 6: `human_reviewed`, `review_comments`
- Phase 7: `migration_plan`
- Phase 8: `validation_results`

#### 4. Metadata
- **trace_metadata**: LangSmith tracing information
- **state_changelog**: History of all state changes
- **error_log**: All errors encountered
- **timestamps**: When state was created/updated

---

## State Lifecycle

### 1. Initialization

**When**: User starts workflow via API
**Where**: `WorkflowOrchestrator.start_workflow()`

```python
# Initial state
{
    "project_id": "pintu-test",
    "state_version": 0,
    "phase": "init",
    "next_node": "",
    "supervisor_reason": "",
    "mcp_request_profile": {},
    "context_pack": {},
    "normalized_docs": [],
    "extracted_facts": {},
    "confidence_scores": {},
    "evidence_map": {},
    "missing_questions": [],
    "answered_questions": [],
    "question_priorities": {},
    "gap_analysis": {},
    "intake_draft": {},
    "human_reviewed": False,
    "review_comments": [],
    "review_flags": [],
    "migration_plan": {},
    "validation_results": {},
    "trace_metadata": {},
    "state_changelog": [],
    "error_log": [],
    "last_error": "",
    "created_at": "2026-05-27T19:00:00Z",
    "updated_at": "2026-05-27T19:00:00Z",
    "last_committed_by": "workflow_orchestrator",
    "last_committed_at": "2026-05-27T19:00:00Z"
}
```

### 2. Execution

**When**: `workflow.ainvoke(state, config)` is called
**How**: LangGraph passes state through nodes

```
┌─────────────────────────────────────────────────────────┐
│  LangGraph Execution Model                              │
│                                                          │
│  1. Start with initial state                            │
│  2. Pass state to first node (supervisor)               │
│  3. Node returns state patch                            │
│  4. LangGraph merges patch into state                   │
│  5. Pass updated state to next node                     │
│  6. Repeat until END node                               │
└─────────────────────────────────────────────────────────┘
```

**Example Flow**:

```python
# Step 1: Initial state
state = {"project_id": "test", "phase": "init", "state_version": 0}

# Step 2: Supervisor node
supervisor_patch = {"next_node": "context_retrieval", "state_version": 1}
state = merge(state, supervisor_patch)
# state = {"project_id": "test", "phase": "init", "next_node": "context_retrieval", "state_version": 1}

# Step 3: Context retrieval node
context_patch = {
    "context_pack": {...},
    "normalized_docs": [doc1, doc2, ...],
    "phase": "context_retrieval",
    "state_version": 2
}
state = merge(state, context_patch)
# state now has all previous fields PLUS new ones

# Step 4: Back to supervisor
supervisor_patch = {"next_node": "extraction", "state_version": 3}
state = merge(state, supervisor_patch)

# ... continues ...
```

### 3. Completion

**When**: Workflow reaches END node
**Result**: Final state with all accumulated data

```python
# Final state (simplified)
{
    "project_id": "pintu-test",
    "state_version": 25,
    "phase": "complete",
    "context_pack": {...},           # From phase 2
    "normalized_docs": [...],        # From phase 2
    "extracted_facts": {...},        # From phase 3
    "confidence_scores": {...},      # From phase 3
    "missing_questions": [...],      # From phase 4
    "intake_draft": {...},           # From phase 5
    "human_reviewed": True,          # From phase 6
    "migration_plan": {...},         # From phase 7
    "validation_results": {...},     # From phase 8
    "updated_at": "2026-05-27T19:05:00Z"
}
```

---

## State Reducers

### What are Reducers?

Reducers define **how state updates are merged**. Without reducers, new values replace old values. With reducers, you can append, merge, or combine values.

### Why Use Reducers?

**Problem**: Multiple agents want to add items to a list

```python
# Without reducer (WRONG)
state["normalized_docs"] = [doc1, doc2]  # Agent 1
state["normalized_docs"] = [doc3, doc4]  # Agent 2 - OVERWRITES!
# Result: [doc3, doc4] - Lost doc1 and doc2!

# With reducer (CORRECT)
state["normalized_docs"] = [doc1, doc2]  # Agent 1
state["normalized_docs"] += [doc3, doc4]  # Agent 2 - APPENDS!
# Result: [doc1, doc2, doc3, doc4] - All docs preserved!
```

### Reducer Implementation

**File**: `backend/app/orchestration/state.py`

```python
from typing import Annotated, List, Any

def merge_lists(left: List[Any], right: List[Any]) -> List[Any]:
    """
    Merge two lists by appending right to left.
    
    Args:
        left: Existing list in state
        right: New list from agent patch
        
    Returns:
        Combined list
    """
    return left + right

# Usage in state schema
class MigrationState(TypedDict):
    # List fields use reducer
    normalized_docs: Annotated[List[Dict[str, Any]], merge_lists]
    missing_questions: Annotated[List[Dict[str, Any]], merge_lists]
    answered_questions: Annotated[List[Dict[str, Any]], merge_lists]
    review_comments: Annotated[List[str], merge_lists]
    review_flags: Annotated[List[str], merge_lists]
    state_changelog: Annotated[List[StateChangelogEntry], merge_lists]
    error_log: Annotated[List[Dict[str, Any]], merge_lists]
    
    # Non-list fields don't need reducer (replace is fine)
    phase: str
    state_version: int
    extracted_facts: Dict[str, Any]
```

### How LangGraph Uses Reducers

```python
# Current state
state = {
    "normalized_docs": [doc1, doc2],
    "phase": "context_retrieval"
}

# Agent returns patch
patch = {
    "normalized_docs": [doc3, doc4],
    "phase": "extraction"
}

# LangGraph merges using reducers
new_state = {
    "normalized_docs": merge_lists([doc1, doc2], [doc3, doc4]),  # Uses reducer
    "phase": "extraction"  # Simple replace (no reducer)
}

# Result
new_state = {
    "normalized_docs": [doc1, doc2, doc3, doc4],  # Appended!
    "phase": "extraction"  # Replaced!
}
```

---

## State Versioning

### Purpose

Track state evolution for:
- Debugging
- Audit trails
- Optimistic locking (during initialization only)

### How It Works

```python
# Initial state
state_version = 0

# After each node
state_version += 1

# Example progression
init → 0
supervisor → 1
context_retrieval → 2
supervisor → 3
extraction → 4
supervisor → 5
questionnaire → 6
# ... and so on
```

### Version Tracking

Each node increments the version:

```python
async def _context_retrieval_node(self, state: MigrationState) -> Dict[str, Any]:
    # Do work...
    
    return {
        "context_pack": context_pack,
        "phase": "context_retrieval",
        "state_version": state["state_version"] + 1,  # Increment
        "updated_at": datetime.utcnow().isoformat()
    }
```

### Important Note

**State versioning is NOT used for optimistic locking during workflow execution**. LangGraph manages state automatically. Versioning is only for:
1. Tracking state evolution
2. Debugging
3. Audit trails
4. Initialization (outside workflow)

---

## State Persistence

### Storage Layers

#### 1. In-Memory (LangGraph)
**During Execution**: LangGraph keeps state in memory
- Fast
- Automatic
- Lost on restart

#### 2. Redis Cache (StateManager)
**For Quick Access**: State manager caches in Redis
- Fast retrieval
- Survives restarts
- TTL-based expiration

```python
# StateManager saves to Redis
await self.state_manager.initialize_state(project_id)
# Stored in Redis: key="migration_state:pintu-test"
```

#### 3. Checkpoints (LangGraph)
**For Resume**: LangGraph saves checkpoints
- Can resume from any point
- Survives restarts
- Stored in MemorySaver (POC) or database (production)

```python
# LangGraph checkpoint
checkpointer = MemorySaver()
workflow = graph.compile(checkpointer=checkpointer)

# Can resume later
config = {"configurable": {"thread_id": project_id}}
workflow.ainvoke(state, config)  # Resumes from checkpoint
```

### State Retrieval

```python
# Get current state
state = await state_manager.get_state(project_id)

# State includes everything
{
    "project_id": "pintu-test",
    "phase": "extraction",
    "context_pack": {...},
    "normalized_docs": [...],
    "extracted_facts": {...},
    # ... all accumulated data
}
```

---

## State Best Practices

### 1. Always Use Patches

**DON'T**:
```python
# Modifying state directly
state["phase"] = "extraction"
state["extracted_facts"] = facts
return state  # Returns full state
```

**DO**:
```python
# Return only changes
return {
    "phase": "extraction",
    "extracted_facts": facts
}  # LangGraph merges this
```

### 2. Use Reducers for Lists

**DON'T**:
```python
normalized_docs: List[Dict[str, Any]]  # Will be replaced
```

**DO**:
```python
normalized_docs: Annotated[List[Dict[str, Any]], merge_lists]  # Will be appended
```

### 3. Include Metadata

Always include:
- `phase`: Current phase
- `state_version`: Incremented version
- `updated_at`: Timestamp
- `last_committed_by`: Agent name

```python
return {
    "extracted_facts": facts,
    "phase": "extraction",
    "state_version": state["state_version"] + 1,
    "updated_at": datetime.utcnow().isoformat(),
    "last_committed_by": "extraction_agent"
}
```

### 4. Validate Input

Always check required fields:

```python
async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
    # Validate
    project_id = state.get("project_id")
    if not project_id:
        raise ValueError("project_id is required")
    
    normalized_docs = state.get("normalized_docs", [])
    if not normalized_docs:
        raise ValueError("No documents to extract from")
    
    # Proceed...
```

---

## Next Steps

- [03-agent-details.md](./03-agent-details.md) - How agents use state
- [04-data-structures.md](./04-data-structures.md) - Detailed data formats
- [05-execution-flow.md](./05-execution-flow.md) - Step-by-step execution