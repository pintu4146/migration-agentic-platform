# Architecture Patterns & Design Decisions

**Purpose**: Document key architectural patterns and design decisions for the Migration Copilot POC.  
**Last Updated**: 2026-05-28  
**Applies To**: All AI agents working on this project  

---

## 🏗️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Project    │  │   Document   │  │   Workflow   │      │
│  │   Selector   │  │    Upload    │  │  Execution   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         └──────────────────┴──────────────────┘              │
│                            │                                 │
│                    ┌───────▼────────┐                        │
│                    │   API Client   │                        │
│                    │  (services/    │                        │
│                    │    api.js)     │                        │
│                    └───────┬────────┘                        │
└────────────────────────────┼──────────────────────────────────┘
                             │ HTTP/SSE
┌────────────────────────────▼──────────────────────────────────┐
│                    Backend (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────┐    │
│  │                   API Layer                          │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │    │
│  │  │ Projects │  │Documents │  │  Orchestration   │  │    │
│  │  │   API    │  │   API    │  │       API        │  │    │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │    │
│  └──────────────────────────────────────────────────────┘    │
│                             │                                 │
│  ┌──────────────────────────▼──────────────────────────┐    │
│  │              Orchestration Layer                     │    │
│  │  ┌────────────────────────────────────────────┐     │    │
│  │  │         LangGraph Workflow                 │     │    │
│  │  │  ┌──────────────┐  ┌──────────────────┐   │     │    │
│  │  │  │  Supervisor  │  │  State Manager   │   │     │    │
│  │  │  └──────────────┘  └──────────────────┘   │     │    │
│  │  └────────────────────────────────────────────┘     │    │
│  └──────────────────────────────────────────────────────┘    │
│                             │                                 │
│  ┌──────────────────────────▼──────────────────────────┐    │
│  │                  Agent Layer                         │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │    │
│  │  │ Context  │  │Extraction│  │  Questionnaire   │  │    │
│  │  │Retrieval │  │  Agent   │  │      Agent       │  │    │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │    │
│  └──────────────────────────────────────────────────────┘    │
│                             │                                 │
│  ┌──────────────────────────▼──────────────────────────┐    │
│  │              Infrastructure Layer                    │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │    │
│  │  │   MCP    │  │  Redis   │  │     Qdrant       │  │    │
│  │  │Connector │  │  Client  │  │  Vector Store    │  │    │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │    │
│  └──────────────────────────────────────────────────────┘    │
│                             │                                 │
│  ┌──────────────────────────▼──────────────────────────┐    │
│  │               Provider Layer                         │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │    │
│  │  │  OpenAI  │  │  Gemini  │  │   LangSmith      │  │    │
│  │  │ Provider │  │ Provider │  │    Tracing       │  │    │
│  │  └──────────┘  └──────────┘  └──────────────────┘  │    │
│  └──────────────────────────────────────────────────────┘    │
└───────────────────────────────────────────────────────────────┘
```

---

## 🎯 Core Design Patterns

### 1. Supervisor Pattern (LangGraph Orchestration)

**Pattern**: Centralized supervisor controls workflow execution and agent coordination.

**Implementation**:
```python
class WorkflowOrchestrator:
    """Supervisor-led LangGraph workflow."""
    
    async def decide_next_node(self, state: MigrationState) -> SupervisorDecision:
        """
        Supervisor decides next node based on current state.
        
        Decision Tree:
        - INIT → context_retrieval
        - CONTEXT_RETRIEVAL → extraction
        - EXTRACTION → questionnaire
        - QUESTIONNAIRE → human_review
        - HUMAN_REVIEW → END (pause for approval)
        """
        current_phase = WorkflowPhase(state["phase"])
        
        if current_phase == WorkflowPhase.INIT:
            return SupervisorDecision(
                next_node="context_retrieval",
                next_phase=WorkflowPhase.CONTEXT_RETRIEVAL,
                reason="Starting workflow"
            )
        # ... more decisions
```

**Benefits**:
- ✅ Single source of truth for workflow logic
- ✅ Clear decision tree
- ✅ Easy to debug and trace
- ✅ Prevents agent chaos

**Anti-Pattern**: Agents deciding their own next steps (leads to unpredictable flow).

---

### 2. State Transaction Pattern

**Pattern**: Treat state updates like database transactions with optimistic locking.

**Implementation**:
```python
# Agent reads state snapshot
async def _extraction_node(self, state: MigrationState) -> Dict[str, Any]:
    """Extract facts from documents."""
    current_version = state["state_version"]
    
    # Agent processes and produces state patch
    result = await agent.execute(state)
    
    # Return patch with version check
    return {
        "extracted_facts": result["facts"],
        "state_version": current_version + 1,  # Increment version
        "updated_at": datetime.utcnow().isoformat(),
        "last_committed_by": "extraction_agent"
    }

# LangGraph applies patch atomically
# If version mismatch, node is re-executed with latest state
```

**Benefits**:
- ✅ Prevents concurrent write conflicts
- ✅ Deterministic state evolution
- ✅ Easy to audit state changes
- ✅ Supports retry logic

**Anti-Pattern**: Direct state mutation without version control.

---

### 3. Provider Abstraction Pattern

**Pattern**: Abstract LLM providers behind a common interface.

**Implementation**:
```python
class BaseLLMProvider(ABC):
    """Abstract base for LLM providers."""
    
    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text completion."""
        pass
    
    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: Type[BaseModel],
        **kwargs
    ) -> BaseModel:
        """Generate structured output."""
        pass

class OpenAIProvider(BaseLLMProvider):
    """OpenAI implementation."""
    # ...

class GeminiProvider(BaseLLMProvider):
    """Gemini implementation."""
    # ...

# Factory pattern for provider selection
def get_llm_provider(provider_name: str) -> BaseLLMProvider:
    if provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "gemini":
        return GeminiProvider()
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
```

**Benefits**:
- ✅ Swap providers without changing agent code
- ✅ Test with mock providers
- ✅ Support multiple providers simultaneously
- ✅ Isolate provider-specific quirks

**Anti-Pattern**: Hardcoding OpenAI or Gemini calls in agent logic.

---

### 4. MCP Connector Pattern

**Pattern**: Centralized, configurable connector for external knowledge sources.

**Implementation**:
```python
class MCPConnector:
    """Configurable MCP connector."""
    
    def __init__(self, config: MCPConfig):
        self.base_url = config.base_url
        self.bearer_token = config.bearer_token
        self.timeout = config.timeout
        self.retry_count = config.retry_count
    
    async def retrieve_context(
        self,
        profile: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Retrieve context using profile configuration.
        
        Profile examples:
        - context_retrieval_profile: Full context for initial retrieval
        - extraction_profile: Technical docs only
        - questionnaire_profile: Requirements and constraints
        """
        profile_config = self._load_profile(profile)
        
        # Apply profile filters
        query = self._build_query(profile_config, filters)
        
        # Execute retrieval with retry logic
        result = await self._execute_with_retry(query)
        
        # Normalize output
        return self._normalize_result(result)
```

**Benefits**:
- ✅ Plug-and-play knowledge sources
- ✅ Profile-based retrieval (different agents, different needs)
- ✅ Centralized retry and error handling
- ✅ Easy to mock for testing

**Anti-Pattern**: Each agent implementing its own MCP client.

---

### 5. Agent Responsibility Pattern

**Pattern**: Each agent has a single, well-defined responsibility.

**Agent Responsibilities**:

| Agent | Responsibility | Input | Output |
|-------|---------------|-------|--------|
| Context Retrieval | Fetch and normalize context | project_id, profile | context_pack, normalized_docs |
| Extraction | Extract structured facts | normalized_docs | extracted_facts, confidence_scores |
| Questionnaire | Identify gaps, generate questions | extracted_facts | gap_analysis, questions |
| Intake Draft | Generate intake document | all above | intake_draft |
| Review | Validate intake | intake_draft | validation_results, review_flags |
| Migration Planning | Generate migration plan | reviewed_intake | migration_plan |

**Implementation**:
```python
class ExtractionAgent:
    """Extract structured facts from documents."""
    
    agent_name = "extraction_agent"
    
    async def execute(self, state: MigrationState) -> Dict[str, Any]:
        """
        Extract facts from normalized documents.
        
        Responsibilities:
        - Parse technical stack
        - Identify dependencies
        - Extract configuration
        - Assign confidence scores
        
        Does NOT:
        - Fetch documents (Context Retrieval Agent)
        - Generate questions (Questionnaire Agent)
        - Draft intake (Intake Draft Agent)
        """
        # Single responsibility implementation
        pass
```

**Benefits**:
- ✅ Clear boundaries
- ✅ Easy to test in isolation
- ✅ Easy to replace or upgrade
- ✅ Prevents scope creep

**Anti-Pattern**: "God agents" that do everything.

---

### 6. Tracing Pattern (LangSmith)

**Pattern**: Comprehensive tracing for every operation.

**Implementation**:
```python
from langsmith import traceable

class ExtractionAgent:
    
    @traceable(
        name="extraction_agent.execute",
        tags=["agent", "extraction"],
        metadata={"agent_name": "extraction_agent"}
    )
    async def execute(self, state: MigrationState) -> Dict[str, Any]:
        """Execute extraction with full tracing."""
        
        # Trace LLM call
        result = await self._extract_with_llm(state)
        
        # Trace validation
        validated = await self._validate_extraction(result)
        
        return validated
    
    @traceable(name="extraction_agent.extract_with_llm")
    async def _extract_with_llm(self, state: MigrationState) -> Dict:
        """Trace LLM extraction."""
        # LLM call automatically traced
        pass
```

**Trace Hierarchy**:
```
workflow_execution
├── context_retrieval_node
│   ├── mcp_connector.retrieve_context
│   │   ├── http_request (retry 1)
│   │   └── http_request (retry 2, success)
│   └── normalize_documents
├── extraction_node
│   ├── extraction_agent.execute
│   │   ├── llm.generate_structured
│   │   └── validate_extraction
│   └── state_commit
└── questionnaire_node
    └── ...
```

**Benefits**:
- ✅ Full execution visibility
- ✅ Debug failures easily
- ✅ Measure performance
- ✅ Demo-friendly observability

**Anti-Pattern**: No tracing or logging.

---

### 7. State Reducer Pattern (LangGraph)

**Pattern**: Use reducers for list fields to prevent overwrites.

**Implementation**:
```python
from typing import Annotated
from operator import add

def merge_lists(existing: List, new: List) -> List:
    """Merge lists without duplicates."""
    return existing + [item for item in new if item not in existing]

class MigrationState(TypedDict):
    """Workflow state with reducers."""
    
    # Simple fields (last write wins)
    project_id: str
    phase: str
    
    # List fields with reducers (merge, don't overwrite)
    normalized_docs: Annotated[List[Dict], merge_lists]
    review_flags: Annotated[List[str], add]  # Simple concatenation
    
    # Dict fields (last write wins, but could use custom reducer)
    extracted_facts: Optional[Dict[str, Any]]
```

**Benefits**:
- ✅ Prevents accidental list overwrites
- ✅ Supports incremental updates
- ✅ Clear merge semantics

**Anti-Pattern**: Manually merging lists in every node.

---

### 8. Human-in-the-Loop Pattern

**Pattern**: Pause workflow for human review, resume after approval.

**Implementation**:
```python
async def _human_review_node(self, state: MigrationState) -> Dict[str, Any]:
    """
    Pause workflow for human review.
    
    Returns human_reviewed=False to signal supervisor to pause.
    """
    logger.info("[human_review_node] Pausing for human review")
    
    return {
        "phase": WorkflowPhase.HUMAN_REVIEW.value,
        "human_reviewed": False,  # ✅ Signal to pause
        "review_required": True,
        "review_message": "Please review intake draft and approve to continue"
    }

async def decide_next_node(self, state: MigrationState) -> SupervisorDecision:
    """Supervisor checks human_reviewed flag."""
    
    if state["phase"] == WorkflowPhase.HUMAN_REVIEW.value:
        if not state.get("human_reviewed", False):
            # Pause workflow
            return SupervisorDecision(
                next_node="END",
                next_phase=WorkflowPhase.HUMAN_REVIEW,
                reason="Waiting for human review"
            )
        else:
            # Resume workflow
            return SupervisorDecision(
                next_node="migration_planning",
                next_phase=WorkflowPhase.MIGRATION_PLANNING,
                reason="Human review approved, continue to planning"
            )
```

**Resume Workflow**:
```python
# API endpoint to resume after approval
@router.post("/projects/{project_id}/workflow/approve")
async def approve_workflow(project_id: str):
    """Approve intake and resume workflow."""
    
    # Update state with approval
    state = await orchestrator.get_state(project_id)
    state["human_reviewed"] = True
    state["approved_by"] = "user@example.com"
    state["approved_at"] = datetime.utcnow().isoformat()
    
    # Resume workflow
    result = await orchestrator.resume_workflow(project_id, state)
    
    return result
```

**Benefits**:
- ✅ Clear pause/resume semantics
- ✅ Human control over critical decisions
- ✅ Audit trail of approvals

**Anti-Pattern**: Automatic progression without human review.

---

### 9. SSE Streaming Pattern

**Pattern**: Real-time updates via Server-Sent Events.

**Implementation**:
```python
# Backend: SSE endpoint with state polling
@router.get("/projects/{project_id}/workflow/stream")
async def stream_workflow_state(project_id: str):
    """Stream workflow state updates via SSE."""
    
    async def event_generator():
        last_version = -1
        last_phase = None
        
        while True:
            # Poll state from Redis
            state = await redis_client.get_state(project_id)
            
            if state:
                current_version = state.get("state_version", 0)
                current_phase = state.get("phase")
                
                # Send update if state changed
                if current_version > last_version:
                    yield {
                        "event": "state_update",
                        "data": json.dumps(state)
                    }
                    last_version = current_version
                
                # Send phase transition event
                if current_phase != last_phase:
                    yield {
                        "event": "phase_transition",
                        "data": json.dumps({
                            "from": last_phase,
                            "to": current_phase,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    }
                    last_phase = current_phase
            
            await asyncio.sleep(0.5)  # Poll every 500ms
    
    return EventSourceResponse(event_generator())

# Frontend: SSE hook
const useWorkflowSSE = (projectId) => {
  const [state, setState] = useState(null);
  
  useEffect(() => {
    const eventSource = new EventSource(
      `/api/projects/${projectId}/workflow/stream`
    );
    
    eventSource.addEventListener('state_update', (event) => {
      setState(JSON.parse(event.data));
    });
    
    eventSource.addEventListener('phase_transition', (event) => {
      const transition = JSON.parse(event.data);
      console.log(`Phase: ${transition.from} → ${transition.to}`);
    });
    
    return () => eventSource.close();
  }, [projectId]);
  
  return { state };
};
```

**Benefits**:
- ✅ Real-time UI updates
- ✅ No polling from frontend
- ✅ Efficient (server pushes only when changed)
- ✅ Demo-friendly (shows live progress)

**Anti-Pattern**: Frontend polling every second.

---

## 🔧 Infrastructure Patterns

### 1. Redis State Synchronization

**Pattern**: Sync LangGraph in-memory state to Redis for SSE access.

**Why**: LangGraph state is in-memory, SSE endpoint needs persistent access.

**Implementation**:
```python
class WorkflowOrchestrator:
    
    async def execute_workflow(self, project_id: str) -> Dict[str, Any]:
        """Execute workflow with Redis sync."""
        
        # Create LangGraph workflow
        workflow = self._create_workflow()
        
        # Stream execution
        async for output in workflow.astream(initial_state):
            # Sync to Redis after each node
            await self.redis_client.set_state(
                project_id,
                output,
                ttl=3600  # 1 hour
            )
        
        return output
```

**Benefits**:
- ✅ SSE can access latest state
- ✅ State persists across requests
- ✅ Supports workflow pause/resume

**Trade-off**: Slight overhead of Redis writes, but acceptable for POC.

---

### 2. Vector Store Pattern (Qdrant)

**Pattern**: Store document embeddings for semantic search.

**Implementation**:
```python
class QdrantClient:
    """Qdrant vector store client."""
    
    async def upsert_documents(
        self,
        project_id: str,
        documents: List[Dict[str, Any]]
    ):
        """Store document embeddings."""
        
        # Generate embeddings
        embeddings = await self.embedding_model.embed_documents(
            [doc["content"] for doc in documents]
        )
        
        # Upsert to Qdrant
        points = [
            PointStruct(
                id=doc["id"],
                vector=embedding,
                payload={
                    "project_id": project_id,
                    "content": doc["content"],
                    "metadata": doc["metadata"]
                }
            )
            for doc, embedding in zip(documents, embeddings)
        ]
        
        await self.client.upsert(
            collection_name="documents",
            points=points
        )
    
    async def search_similar(
        self,
        project_id: str,
        query: str,
        limit: int = 10
    ) -> List[Dict]:
        """Search similar documents."""
        
        # Generate query embedding
        query_embedding = await self.embedding_model.embed_query(query)
        
        # Search Qdrant
        results = await self.client.search(
            collection_name="documents",
            query_vector=query_embedding,
            query_filter={
                "must": [
                    {"key": "project_id", "match": {"value": project_id}}
                ]
            },
            limit=limit
        )
        
        return [hit.payload for hit in results]
```

**Benefits**:
- ✅ Semantic search over documents
- ✅ Project-scoped retrieval
- ✅ Fast similarity search

---

## 📊 Data Flow Patterns

### End-to-End Data Flow

```
1. User uploads documents
   ↓
2. Documents parsed and chunked
   ↓
3. Chunks embedded and stored in Qdrant
   ↓
4. User starts workflow
   ↓
5. Context Retrieval Agent:
   - Fetches from MCP (Confluence)
   - Fetches from Qdrant (uploaded docs)
   - Normalizes into context_pack
   ↓
6. Extraction Agent:
   - Reads context_pack
   - Extracts structured facts
   - Assigns confidence scores
   ↓
7. Questionnaire Agent:
   - Identifies gaps in facts
   - Generates prioritized questions
   ↓
8. Intake Draft Agent:
   - Generates intake document
   ↓
9. Review Agent:
   - Validates intake
   - Flags issues
   ↓
10. Human Review:
    - Workflow pauses
    - User reviews intake
    - User approves or rejects
    ↓
11. Migration Planning Agent:
    - Generates migration plan
    - Recommends cloud infrastructure
    ↓
12. Final output ready for export
```

---

## 🚨 Critical Design Decisions

### Decision 1: Hybrid SSE Architecture

**Problem**: LangGraph state is in-memory, SSE needs persistent access.

**Options**:
1. Pure LangGraph streaming (no Redis)
2. Redis-only state (no LangGraph streaming)
3. Hybrid: LangGraph streaming + Redis sync

**Chosen**: Hybrid approach

**Rationale**:
- LangGraph streaming provides real-time node outputs
- Redis sync enables SSE polling from separate endpoint
- Acceptable overhead for POC
- Supports pause/resume

**Trade-off**: Slight complexity, but best of both worlds.

---

### Decision 2: State Transaction Pattern

**Problem**: Multiple agents could overwrite shared state concurrently.

**Options**:
1. Free-for-all state mutation
2. Locking mechanisms
3. Optimistic locking with version numbers

**Chosen**: Optimistic locking with state_version

**Rationale**:
- Deterministic state evolution
- Easy to debug
- Supports retry logic
- No complex locking

**Trade-off**: Nodes may re-execute if version mismatch, but rare in practice.

---

### Decision 3: Provider Abstraction

**Problem**: Need to support multiple LLM providers.

**Options**:
1. Hardcode OpenAI
2. Hardcode Gemini
3. Abstract provider interface

**Chosen**: Abstract provider interface

**Rationale**:
- Swap providers without changing agent code
- Test with mock providers
- Support multiple providers
- Future-proof

**Trade-off**: Slight abstraction overhead, but worth it.

---

## 📚 References

- **LangGraph Docs**: https://langchain-ai.github.io/langgraph/
- **LangSmith Docs**: https://docs.smith.langchain.com/
- **IBM Carbon**: https://carbondesignsystem.com/
- **FastAPI**: https://fastapi.tiangolo.com/
- **Qdrant**: https://qdrant.tech/documentation/

---

**Last Updated**: 2026-05-28  
**Maintained By**: AI Agents Team  
**Status**: Active - Reference for all architectural decisions