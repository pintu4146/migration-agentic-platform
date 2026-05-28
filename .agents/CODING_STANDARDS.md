# Coding Standards & Best Practices

**Purpose**: Enforce consistent coding patterns across the Migration Copilot codebase.  
**Last Updated**: 2026-05-28  
**Applies To**: All AI agents working on this project  

---

## 🎯 Core Principles

1. **SOLID Principles**: Every class has a single responsibility
2. **KISS**: Keep it simple, this is a POC not production
3. **DRY**: Don't repeat yourself
4. **Explicit over Implicit**: Be clear about types, colors, field names
5. **Fail Fast**: Validate early, log errors clearly

---

## 📁 Project Structure Standards

### Backend Structure
```
backend/app/
├── agents/          # LangGraph agent implementations
├── api/             # FastAPI endpoints
├── embeddings/      # Document chunking and embedding
├── mcp/             # MCP connector and tools
├── models/          # Pydantic schemas
├── orchestration/   # LangGraph workflow and state
├── parsers/         # Document parsers
├── providers/       # LLM provider abstraction
├── storage/         # Redis and Qdrant clients
└── tracing/         # LangSmith tracing
```

### Frontend Structure
```
frontend/src/
├── components/      # Reusable React components
├── hooks/           # Custom React hooks
├── pages/           # Page components
├── services/        # API client
└── utils/           # Helper functions
```

---

## 🐍 Python Coding Standards

### 1. Type Hints (MANDATORY)
```python
# ✅ CORRECT - Full type hints
async def retrieve_context(
    self,
    project_id: str,
    profile: str = "context_retrieval_profile"
) -> Dict[str, Any]:
    """Retrieve context for project."""
    pass

# ❌ WRONG - No type hints
async def retrieve_context(self, project_id, profile="context_retrieval_profile"):
    pass
```

### 2. Docstrings (MANDATORY for public methods)
```python
# ✅ CORRECT - Clear docstring
async def execute_workflow(
    self,
    project_id: str,
    mcp_profile: str = "context_retrieval_profile"
) -> Dict[str, Any]:
    """
    Execute workflow for project.
    
    Args:
        project_id: Unique project identifier
        mcp_profile: MCP retrieval profile name
        
    Returns:
        Final workflow state
        
    Raises:
        ValueError: If project doesn't exist
        GraphRecursionError: If workflow hits recursion limit
    """
    pass

# ❌ WRONG - No docstring
async def execute_workflow(self, project_id: str, mcp_profile: str = "context_retrieval_profile"):
    pass
```

### 3. Error Handling
```python
# ✅ CORRECT - Specific exceptions, clear logging
try:
    result = await self.llm.generate_structured(prompt, schema)
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse JSON: {e}")
    raise ValueError(f"Invalid JSON response: {str(e)}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise

# ❌ WRONG - Bare except, no logging
try:
    result = await self.llm.generate_structured(prompt, schema)
except:
    pass
```

### 4. Logging Standards
```python
# ✅ CORRECT - Structured logging with context
logger.info(
    f"[{self.agent_name}] Extracted {len(facts)} facts "
    f"(avg confidence: {avg_confidence:.2f})"
)

logger.error(
    f"[{self.agent_name}] Error: {str(e)}",
    exc_info=True  # Include stack trace
)

# ❌ WRONG - Vague logging
logger.info("Done")
logger.error("Error")
```

### 5. Async/Await Patterns
```python
# ✅ CORRECT - Proper async/await
async def process_documents(self, docs: List[Dict]) -> List[Dict]:
    results = []
    for doc in docs:
        result = await self.process_single(doc)  # Await each
        results.append(result)
    return results

# ❌ WRONG - Missing await
async def process_documents(self, docs: List[Dict]) -> List[Dict]:
    results = []
    for doc in docs:
        result = self.process_single(doc)  # Missing await!
        results.append(result)
    return results
```

---

## ⚛️ React/Frontend Standards

### 1. Component Structure
```jsx
// ✅ CORRECT - Clear structure
import { useState, useEffect } from 'react';
import { Button, Tile } from '@carbon/react';
import './ComponentName.scss';

const ComponentName = ({ prop1, prop2 }) => {
  const [state, setState] = useState(null);
  
  useEffect(() => {
    // Effect logic
  }, [dependencies]);
  
  const handleAction = () => {
    // Handler logic
  };
  
  return (
    <div className="component-name">
      {/* JSX */}
    </div>
  );
};

export default ComponentName;
```

### 2. Hooks Usage
```jsx
// ✅ CORRECT - Custom hook with cleanup
const useWorkflowSSE = (projectId) => {
  const [state, setState] = useState(null);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    const eventSource = new EventSource(`/api/stream/${projectId}`);
    
    eventSource.onmessage = (event) => {
      setState(JSON.parse(event.data));
    };
    
    // ✅ Cleanup
    return () => {
      eventSource.close();
    };
  }, [projectId]);
  
  return { state, error };
};

// ❌ WRONG - No cleanup
const useWorkflowSSE = (projectId) => {
  const [state, setState] = useState(null);
  
  useEffect(() => {
    const eventSource = new EventSource(`/api/stream/${projectId}`);
    eventSource.onmessage = (event) => {
      setState(JSON.parse(event.data));
    };
    // Missing cleanup!
  }, [projectId]);
  
  return { state };
};
```

### 3. SCSS Standards
```scss
// ✅ CORRECT - Explicit colors, BEM naming
.workflow-execution {
  background: #ffffff;
  
  &__header {
    color: #161616;
    font-size: 1.25rem;
    font-weight: 600;
  }
  
  &__content {
    color: #525252;
    line-height: 1.6;
  }
  
  &--loading {
    opacity: 0.6;
  }
}

// ❌ WRONG - Vague colors, no structure
.page {
  background: white;
  
  .title {
    color: black;
  }
}
```

---

## 🔄 LangGraph Workflow Standards

### 1. Node Implementation
```python
# ✅ CORRECT - Clear node with logging and error handling
async def _extraction_node(self, state: MigrationState) -> Dict[str, Any]:
    """Extract facts from documents."""
    logger.info(f"[extraction_node] Starting fact extraction for project: {state['project_id']}")
    
    try:
        agent = ExtractionAgent()
        result = await agent.execute(state)
        
        logger.info(
            f"[extraction_node] Extracted {len(result.get('extracted_facts', {}))} facts"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"[extraction_node] Error: {e}", exc_info=True)
        return {
            "phase": WorkflowPhase.ERROR.value,
            "last_error": str(e),
            "retry_count": state.get("retry_count", 0) + 1
        }

# ❌ WRONG - No logging, no error handling
async def _extraction_node(self, state: MigrationState):
    agent = ExtractionAgent()
    return await agent.execute(state)
```

### 2. Supervisor Decision Logic
```python
# ✅ CORRECT - Clear decision tree with logging
async def decide_next_node(self, state: MigrationState) -> SupervisorDecision:
    """Decide next node based on current state."""
    current_phase = WorkflowPhase(state["phase"])
    
    logger.info(
        f"[supervisor] Current phase: {current_phase.value}, "
        f"version: {state['state_version']}"
    )
    
    # Check for errors first
    if current_phase == WorkflowPhase.ERROR:
        return await self._handle_error(state)
    
    # Normal flow with explicit conditions
    if current_phase == WorkflowPhase.INIT:
        return SupervisorDecision(
            next_node="context_retrieval",
            next_phase=WorkflowPhase.CONTEXT_RETRIEVAL,
            reason="Starting workflow: retrieve context"
        )
    
    # ... more conditions
    
    logger.info(
        f"[supervisor] Decision: next_node={decision.next_node}, "
        f"reason={decision.reason}"
    )
    
    return decision

# ❌ WRONG - No logging, unclear logic
async def decide_next_node(self, state):
    if state["phase"] == "init":
        return SupervisorDecision("context_retrieval", "context_retrieval", "start")
    # ...
```

### 3. State Updates
```python
# ✅ CORRECT - Explicit state patch with all metadata
return {
    "phase": WorkflowPhase.EXTRACTION.value,
    "extracted_facts": facts_dict,
    "confidence_scores": confidence_dict,
    "state_version": state["state_version"] + 1,
    "updated_at": datetime.utcnow().isoformat(),  # ✅ ISO string
    "last_committed_by": self.agent_name,
    "last_committed_at": datetime.utcnow().isoformat(),  # ✅ ISO string
    "trace_metadata": {
        "agent": self.agent_name,
        "facts_count": len(facts_dict),
        "timestamp": datetime.utcnow().isoformat()
    }
}

# ❌ WRONG - Incomplete state update
return {
    "extracted_facts": facts_dict
    # Missing: phase, version, timestamps, metadata
}
```

---

## 🎨 UI/UX Standards

### 1. IBM Carbon Design System
```jsx
// ✅ CORRECT - Use Carbon components
import { Button, Tile, Loading, InlineNotification } from '@carbon/react';
import { Play, CheckmarkFilled } from '@carbon/icons-react';

<Button
  kind="primary"
  size="default"
  renderIcon={Play}
  onClick={handleExecute}
>
  Execute Workflow
</Button>

// ❌ WRONG - Custom button instead of Carbon
<button className="custom-button" onClick={handleExecute}>
  Execute
</button>
```

### 2. Color Standards (IBM Carbon)
```scss
// ✅ CORRECT - Use IBM Carbon color tokens
$text-primary: #161616;    // Main text
$text-secondary: #525252;  // Secondary text
$text-tertiary: #8d8d8d;   // Tertiary text
$ui-background: #ffffff;   // Background
$ui-01: #f4f4f4;          // Container background
$ui-02: #ffffff;          // Secondary container
$ui-03: #e0e0e0;          // Border
$interactive-01: #0f62fe; // Primary blue
$support-01: #da1e28;     // Error red
$support-02: #24a148;     // Success green
$support-03: #f1c21b;     // Warning yellow

// ❌ WRONG - Random colors
$text: #333;
$bg: #fff;
$blue: #007bff;
```

### 3. Accessibility
```jsx
// ✅ CORRECT - Accessible markup
<button
  aria-label="Execute workflow for project"
  aria-busy={executing}
  disabled={executing}
>
  {executing ? 'Executing...' : 'Execute'}
</button>

// ❌ WRONG - No accessibility
<button disabled={executing}>
  Execute
</button>
```

---

## 📊 State Management Standards

### 1. TypedDict Schema
```python
# ✅ CORRECT - Complete schema with annotations
class MigrationState(TypedDict):
    """Complete workflow state."""
    
    # Identity & Version Control
    project_id: str
    state_version: int
    phase: WorkflowPhase
    created_at: str  # ✅ String, not datetime
    updated_at: str  # ✅ String, not datetime
    
    # Context
    context_pack: Optional[Dict[str, Any]]
    normalized_docs: Annotated[List[Dict[str, Any]], merge_lists]
    
    # Extraction
    extracted_facts: Optional[Dict[str, Any]]
    
    # ... all fields documented

# ❌ WRONG - Incomplete schema
class MigrationState(TypedDict):
    project_id: str
    phase: str
    # Missing many fields!
```

### 2. State Initialization
```python
# ✅ CORRECT - Initialize ALL fields
def create_initial_state(project_id: str) -> MigrationState:
    now = datetime.utcnow().isoformat()
    
    return MigrationState(
        # Initialize EVERY field from schema
        project_id=project_id,
        state_version=0,
        phase=WorkflowPhase.INIT,
        created_at=now,
        updated_at=now,
        context_pack=None,
        normalized_docs=[],
        extracted_facts=None,
        gap_analysis=None,  # Don't forget!
        # ... ALL fields
    )

# ❌ WRONG - Missing fields
def create_initial_state(project_id: str):
    return {
        "project_id": project_id,
        "phase": "init"
        # Missing most fields!
    }
```

---

## 🧪 Testing Standards

### 1. Test Structure
```python
# ✅ CORRECT - Clear test with setup, action, assert
async def test_context_retrieval_success():
    """Test successful context retrieval."""
    # Setup
    agent = ContextRetrievalAgent()
    state = create_initial_state("test-project")
    
    # Action
    result = await agent.retrieve_context(state)
    
    # Assert
    assert result["context_pack"] is not None
    assert len(result["normalized_docs"]) > 0
    assert result["phase"] == WorkflowPhase.CONTEXT_RETRIEVAL.value

# ❌ WRONG - Unclear test
async def test_retrieval():
    agent = ContextRetrievalAgent()
    result = await agent.retrieve_context({})
    assert result
```

---

## 📝 Documentation Standards

### 1. Code Comments
```python
# ✅ CORRECT - Explain WHY, not WHAT
# Strip markdown code blocks because Gemini wraps JSON in ```json
if content.startswith('```'):
    lines = content.split('\n')
    # ...

# ❌ WRONG - Obvious comment
# Check if content starts with backticks
if content.startswith('```'):
    # ...
```

### 2. README Structure
```markdown
# ✅ CORRECT - Clear structure
# Component Name

## Purpose
Brief description of what this does.

## Usage
```python
# Example code
```

## API
- `method_name(param)`: Description

## Error Handling
- `ValueError`: When X happens
- `KeyError`: When Y is missing

## Testing
```bash
pytest tests/test_component.py
```

# ❌ WRONG - Vague README
# Component
Does stuff.
```

---

## 🚫 Anti-Patterns to AVOID

### 1. Datetime Objects in JSON
```python
# ❌ NEVER DO THIS
return {
    "created_at": datetime.utcnow()  # Will fail JSON serialization!
}

# ✅ ALWAYS DO THIS
return {
    "created_at": datetime.utcnow().isoformat()  # ISO string
}
```

### 2. Bare Except Clauses
```python
# ❌ NEVER DO THIS
try:
    result = await operation()
except:  # Catches everything, even KeyboardInterrupt!
    pass

# ✅ ALWAYS DO THIS
try:
    result = await operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    raise
```

### 3. Mutable Default Arguments
```python
# ❌ NEVER DO THIS
def process_items(items=[]):  # Mutable default!
    items.append("new")
    return items

# ✅ ALWAYS DO THIS
def process_items(items=None):
    if items is None:
        items = []
    items.append("new")
    return items
```

### 4. String Concatenation in Loops
```python
# ❌ NEVER DO THIS
result = ""
for item in items:
    result += str(item)  # Creates new string each time!

# ✅ ALWAYS DO THIS
result = "".join(str(item) for item in items)
```

---

## ✅ Pre-Commit Checklist

Before committing code, verify:

- [ ] All functions have type hints
- [ ] Public methods have docstrings
- [ ] No datetime objects in JSON-serializable structures
- [ ] All exceptions are logged
- [ ] No bare except clauses
- [ ] All state fields are initialized
- [ ] UI colors are explicit (no defaults)
- [ ] Tests pass
- [ ] No console.log() in production code
- [ ] No commented-out code
- [ ] Imports are organized

---

## 📚 Reference

- **Bug Memory**: `.agents/CRITICAL_BUGS_MEMORY.md`
- **Architecture**: `docs/00-architecture-overview.md`
- **Workflow**: `docs/workflow/01-workflow-overview.md`
- **IBM Carbon**: https://carbondesignsystem.com/

---

**Last Updated**: 2026-05-28  
**Maintained By**: AI Agents Team  
**Status**: Active - Enforce on all new code