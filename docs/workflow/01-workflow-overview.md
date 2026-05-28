# Workflow Overview - Enterprise Application Modernization Copilot

## Table of Contents
1. [Introduction](#introduction)
2. [High-Level Architecture](#high-level-architecture)
3. [Workflow Phases](#workflow-phases)
4. [Data Flow](#data-flow)
5. [Key Components](#key-components)

---

## Introduction

The Enterprise Application Modernization Copilot uses a **LangGraph-based multi-agent orchestration system** to analyze legacy applications and generate migration plans. This document provides a comprehensive overview of how the workflow operates.

### What is LangGraph?

LangGraph is a framework for building stateful, multi-agent workflows. Think of it as a **state machine** where:
- **Nodes** = Individual processing steps (agents)
- **Edges** = Transitions between steps
- **State** = Shared data that flows through the workflow
- **Supervisor** = Decision-maker that routes to the next step

### Why Multi-Agent?

Instead of one monolithic AI trying to do everything, we break the task into specialized agents:
- **Context Retrieval Agent** → Gathers documents
- **Extraction Agent** → Extracts technical facts
- **Questionnaire Agent** → Identifies gaps
- **Intake Draft Agent** → Creates summary
- **Review Agent** → Validates quality
- **Migration Planning Agent** → Generates migration plan

Each agent is an expert in its domain, making the system more reliable and maintainable.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER REQUEST                             │
│              "Analyze my application"                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  FASTAPI BACKEND                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         POST /api/orchestration/execute              │   │
│  └──────────────────┬───────────────────────────────────┘   │
│                     │                                        │
│                     ▼                                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         WorkflowOrchestrator                         │   │
│  │  • Initializes workflow                              │   │
│  │  • Validates project exists                          │   │
│  │  • Executes LangGraph workflow                       │   │
│  └──────────────────┬───────────────────────────────────┘   │
└────────────────────┼────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              LANGGRAPH WORKFLOW ENGINE                       │
│                                                              │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐          │
│  │Supervisor│─────▶│  Node 1  │─────▶│Supervisor│          │
│  │          │      │ (Agent)  │      │          │          │
│  └──────────┘      └──────────┘      └────┬─────┘          │
│       │                                    │                │
│       │                                    ▼                │
│       │            ┌──────────┐      ┌──────────┐          │
│       └───────────▶│  Node 2  │─────▶│Supervisor│          │
│                    │ (Agent)  │      │          │          │
│                    └──────────┘      └──────────┘          │
│                                                              │
│  State flows through each node, getting enriched            │
└─────────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  SHARED STATE                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  MigrationState (TypedDict)                          │   │
│  │  • project_id                                        │   │
│  │  • phase (init → context → extraction → ...)        │   │
│  │  • context_pack (documents)                          │   │
│  │  • extracted_facts                                   │   │
│  │  • missing_questions                                 │   │
│  │  • intake_draft                                      │   │
│  │  • migration_plan                                    │   │
│  │  • state_version (for tracking)                      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Workflow Phases

The workflow progresses through these phases:

### Phase 1: INIT
**Purpose**: Initialize the workflow
- **Input**: `project_id`
- **Output**: Empty state with `phase="init"`
- **Next**: Context Retrieval

### Phase 2: CONTEXT_RETRIEVAL
**Purpose**: Gather all relevant documents
- **Agent**: Context Retrieval Agent
- **Sources**: 
  1. MCP (IBM Context Studio) - Primary
  2. Uploaded Documents (Qdrant) - Fallback
  3. Cached Context - Last resort
- **Output**: `context_pack` with 29 documents
- **Next**: Extraction

### Phase 3: EXTRACTION
**Purpose**: Extract technical facts from documents
- **Agent**: Extraction Agent
- **Input**: `normalized_docs` (29 documents)
- **Process**: 
  1. Build extraction prompt
  2. Call LLM (OpenAI/Gemini)
  3. Parse structured output
  4. Assign confidence scores
  5. Map facts to evidence
- **Output**: `extracted_facts`, `confidence_scores`, `evidence_map`
- **Next**: Questionnaire

### Phase 4: QUESTIONNAIRE
**Purpose**: Identify information gaps
- **Agent**: Questionnaire Agent
- **Input**: `extracted_facts`, `confidence_scores`
- **Process**:
  1. Find low-confidence facts (<0.7)
  2. Find missing required fields
  3. Generate prioritized questions
- **Output**: `missing_questions`, `gap_analysis`
- **Next**: Intake Draft

### Phase 5: INTAKE_DRAFT
**Purpose**: Create structured intake document
- **Agent**: Intake Draft Agent (Phase 5 - Not yet implemented)
- **Input**: `extracted_facts`, `missing_questions`
- **Output**: `intake_draft`
- **Next**: Human Review

### Phase 6: HUMAN_REVIEW
**Purpose**: Pause for human validation
- **Gate**: Human review checkpoint
- **Input**: `intake_draft`
- **Output**: `human_reviewed=true`, `review_comments`
- **Next**: Migration Planning

### Phase 7: MIGRATION_PLANNING
**Purpose**: Generate migration strategy
- **Agent**: Migration Planning Agent (Phase 6 - Not yet implemented)
- **Input**: Reviewed `intake_draft`
- **Output**: `migration_plan` with cloud recommendations
- **Next**: Validation

### Phase 8: VALIDATION
**Purpose**: Final quality check
- **Agent**: Validation Agent
- **Input**: `migration_plan`
- **Output**: `validation_results`
- **Next**: Complete

### Phase 9: COMPLETE
**Purpose**: Finalize workflow
- **Output**: Final state with all results
- **Status**: Workflow complete

---

## Data Flow

### How Data Moves Through the Workflow

```
User Request
    │
    ▼
┌─────────────────────┐
│  project_id         │
│  "pintu-test"       │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│  PHASE: INIT                                            │
│  State: { project_id, phase="init", state_version=0 }  │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│  PHASE: CONTEXT_RETRIEVAL                               │
│  Agent: Context Retrieval Agent                         │
│  Action: Fetch 29 documents from Qdrant                 │
│  State Update:                                          │
│    + context_pack: { documents: [...29 docs...] }      │
│    + normalized_docs: [...29 docs...]                  │
│    + phase: "context_retrieval"                        │
│    + state_version: 2                                  │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│  PHASE: EXTRACTION                                      │
│  Agent: Extraction Agent                                │
│  Action: Extract facts using LLM                        │
│  State Update:                                          │
│    + extracted_facts: {                                │
│        technical_stack: [...],                         │
│        dependencies: [...],                            │
│        deployment_strategy: [...]                      │
│      }                                                  │
│    + confidence_scores: { fact_id: 0.85, ... }        │
│    + evidence_map: { fact_id: [doc_ids], ... }        │
│    + phase: "extraction"                               │
│    + state_version: 4                                  │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│  PHASE: QUESTIONNAIRE                                   │
│  Agent: Questionnaire Agent                             │
│  Action: Generate questions for gaps                    │
│  State Update:                                          │
│    + missing_questions: [                              │
│        { question, priority, gap_type },               │
│        ...                                             │
│      ]                                                  │
│    + gap_analysis: { low_confidence: 5, missing: 3 }  │
│    + phase: "questionnaire"                            │
│    + state_version: 6                                  │
└──────┬──────────────────────────────────────────────────┘
       │
       ▼
     [... continues through remaining phases ...]
```

### State Accumulation

**Key Concept**: State is **additive**. Each agent adds new fields without removing old ones.

```python
# After Context Retrieval
state = {
    "project_id": "pintu-test",
    "phase": "context_retrieval",
    "context_pack": {...},
    "normalized_docs": [...]
}

# After Extraction (adds to existing state)
state = {
    "project_id": "pintu-test",
    "phase": "extraction",
    "context_pack": {...},           # Still here
    "normalized_docs": [...],        # Still here
    "extracted_facts": {...},        # NEW
    "confidence_scores": {...},      # NEW
    "evidence_map": {...}            # NEW
}

# After Questionnaire (adds more)
state = {
    "project_id": "pintu-test",
    "phase": "questionnaire",
    "context_pack": {...},           # Still here
    "normalized_docs": [...],        # Still here
    "extracted_facts": {...},        # Still here
    "confidence_scores": {...},      # Still here
    "evidence_map": {...},           # Still here
    "missing_questions": [...],      # NEW
    "gap_analysis": {...}            # NEW
}
```

---

## Key Components

### 1. WorkflowOrchestrator
**File**: `backend/app/orchestration/workflow.py`

**Responsibilities**:
- Build LangGraph workflow
- Initialize agents
- Execute workflow
- Manage checkpointing

**Key Methods**:
- `start_workflow()` - Initialize state
- `execute_workflow()` - Run the graph
- `_build_graph()` - Define nodes and edges

### 2. Supervisor
**File**: `backend/app/orchestration/supervisor.py`

**Responsibilities**:
- Decide next node based on current phase
- Handle retries
- Route to appropriate agent

**Decision Logic**:
```python
if phase == "init":
    return "context_retrieval"
elif phase == "context_retrieval":
    if context_pack exists:
        return "extraction"
    else:
        return "context_retrieval"  # Retry
elif phase == "extraction":
    if extracted_facts exists:
        return "questionnaire"
    else:
        return "extraction"  # Retry
# ... and so on
```

### 3. Agents
Each agent follows the same pattern:

```python
class SomeAgent:
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Validate input
        project_id = state.get("project_id")
        
        # 2. Do work
        result = await self._do_work(state)
        
        # 3. Return state patch
        return {
            "new_field": result,
            "phase": "next_phase",
            "last_committed_by": "agent_name"
        }
```

### 4. State Manager
**File**: `backend/app/orchestration/state_manager.py`

**Responsibilities**:
- Initialize state
- Get/set state
- Manage checkpoints
- Handle state versioning (for initialization only)

**Note**: During workflow execution, LangGraph manages state automatically. State manager is only used for initialization and external state access.

### 5. LangGraph State Reducers
**File**: `backend/app/orchestration/state.py`

**Purpose**: Define how state updates are merged

```python
from typing import Annotated

def merge_lists(left: List, right: List) -> List:
    """Append right to left"""
    return left + right

class MigrationState(TypedDict):
    # Lists use reducers
    normalized_docs: Annotated[List[Dict], merge_lists]
    missing_questions: Annotated[List[Dict], merge_lists]
    
    # Simple fields are replaced
    phase: str
    state_version: int
```

**How it works**:
- Without reducer: `state["phase"] = "extraction"` → Replaces old value
- With reducer: `state["normalized_docs"] += [new_doc]` → Appends to list

---

## Next Steps

For detailed information, see:
- [02-state-management.md](./02-state-management.md) - Deep dive into state
- [03-agent-details.md](./03-agent-details.md) - Each agent explained
- [04-data-structures.md](./04-data-structures.md) - All data formats
- [05-execution-flow.md](./05-execution-flow.md) - Step-by-step execution
- [06-error-handling.md](./06-error-handling.md) - Error handling and retries