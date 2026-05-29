# Enterprise Application Modernization Copilot - Architecture Overview

## Executive Summary

This document provides a comprehensive architectural overview of the POC enterprise application modernization copilot system. The system uses a multi-agent orchestration approach with LangGraph to automate the migration planning process from source document ingestion to final migration plan generation.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                           │
│              React + IBM Carbon Design System                    │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Real-Time SSE Connection                     │  │
│  │         (Server-Sent Events for Live Updates)             │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │ REST API + SSE
┌────────────────────────▼────────────────────────────────────────┐
│                      FastAPI Backend                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │           LangGraph Orchestration Engine                  │  │
│  │                                                            │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │ Supervisor   │  │ Context      │  │ Extraction   │  │  │
│  │  │ Agent        │  │ Retrieval    │  │ Agent        │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │  │
│  │                                                            │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │ Questionnaire│  │ Intake Draft │  │ Review       │  │  │
│  │  │ Agent        │  │ Agent        │  │ Agent        │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │  │
│  │                                                            │  │
│  │  ┌──────────────┐                                         │  │
│  │  │ Migration    │                                         │  │
│  │  │ Planning     │                                         │  │
│  │  │ Agent        │                                         │  │
│  │  └──────────────┘                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              LangGraph State Management                   │  │
│  │    (Built-in Reducers + State Synchronization)            │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                │                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Redis State Synchronization                  │  │
│  │    (LangGraph In-Memory → Redis for SSE Access)           │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────┬───────────────────┬─────────────────────┘
                       │                   │
        ┌──────────────▼──────┐   ┌───────▼──────────┐
        │  MCP Connector      │   │  LLM Provider    │
        │  (Confluence Cloud) │   │  Abstraction     │
        └──────────────┬──────┘   └───────┬──────────┘
                       │                   │
        ┌──────────────▼──────┐   ┌───────▼──────────┐
        │  Qdrant Vector      │   │  OpenAI/Gemini   │
        │  Store (In-Memory)  │   │  with Fallback   │
        └─────────────────────┘   └──────────────────┘
                       │
        ┌──────────────▼──────────────────┐
        │      LangSmith Tracing           │
        │  (All Nodes, Transitions, State) │
        └──────────────────────────────────┘
```

## Core Design Principles

### 1. Supervisor-Led Orchestration
- Single orchestrator controls workflow
- Agents do not communicate directly
- All transitions go through supervisor
- Deterministic execution flow

### 2. LangGraph State Management
- Built-in state reducers (merge_lists, merge_dicts)
- Automatic state merging and conflict resolution
- State synchronization to Redis for SSE
- Changelog tracking for audit trail
- Type-safe state updates with Annotated types

### 3. Plug-and-Play Architecture
- MCP connector with retrieval profiles
- Provider abstraction (OpenAI/Gemini)
- Configurable through environment variables
- No hardcoded dependencies

### 4. Complete Traceability
- LangSmith traces every operation
- State transitions logged
- Evidence mapping preserved
- Confidence scores tracked

### 5. Human-in-the-Loop
- Review checkpoint before planning
- Feedback integration
- Approval workflow
- Audit trail

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React + Carbon Design | Enterprise UI |
| Real-Time Updates | Server-Sent Events (SSE) | Live workflow progress |
| API | FastAPI | REST endpoints |
| Orchestration | LangGraph | Workflow engine |
| State Sync | Redis | State persistence for SSE |
| LLM | OpenAI + Gemini | Text generation |
| Context Source | Confluence Cloud | Document retrieval |
| Vector Store | Qdrant (in-memory) | Semantic search |
| Tracing | LangSmith | Observability |
| Container | Podman | Runtime |

## Workflow Phases

```
INIT → CONTEXT_RETRIEVAL → EXTRACTION → QUESTIONNAIRE → 
INTAKE_DRAFT → HUMAN_REVIEW → MIGRATION_PLANNING → VALIDATION → COMPLETE
```

### Phase Transitions

1. **INIT → CONTEXT_RETRIEVAL**: System initialized, ready to fetch documents
2. **CONTEXT_RETRIEVAL → EXTRACTION**: Documents normalized, ready for analysis
3. **EXTRACTION → QUESTIONNAIRE**: Facts extracted, identify gaps
4. **QUESTIONNAIRE → INTAKE_DRAFT**: Questions generated, draft document
5. **INTAKE_DRAFT → HUMAN_REVIEW**: Draft complete, await approval
6. **HUMAN_REVIEW → MIGRATION_PLANNING**: Approved, generate plan
7. **MIGRATION_PLANNING → VALIDATION**: Plan generated, final checks
8. **VALIDATION → COMPLETE**: All validated, workflow complete

## Agent Responsibilities

| Agent | Input | Output | Purpose |
|-------|-------|--------|---------|
| Supervisor | Current state | Next node | Route workflow |
| Context Retrieval | MCP profile | Context pack | Fetch documents |
| Extraction | Normalized docs | Structured facts | Extract information |
| Questionnaire | Facts + confidence | Questions | Identify gaps |
| Intake Draft | Facts + questions | Draft document | Generate intake |
| Review | Intake draft | Validation results | Check quality |
| Migration Planning | Approved intake | Migration plan | Generate strategy |

## State Schema

```typescript
interface MigrationState {
  // Identity & Version
  project_id: string;
  state_version: number;
  phase: WorkflowPhase;
  
  // Context
  mcp_request_profile?: object;
  context_pack?: object;
  normalized_docs: object[];
  
  // Extraction
  extracted_facts?: object;
  confidence_scores?: Record<string, number>;
  evidence_map?: Record<string, string[]>;
  
  // Questionnaire
  missing_questions: object[];
  question_priorities?: Record<string, number>;
  
  // Intake
  intake_draft?: object;
  human_reviewed: boolean;
  review_comments: string[];
  
  // Planning
  migration_plan?: object;
  
  // Validation
  validation_results?: object;
  review_flags: string[];
  
  // Traceability
  trace_metadata: object;
  state_changelog: object[];
  last_committed_by: string;
  last_committed_at: string;
  
  // Error Handling
  retry_count: number;
  error_log: object[];
}
```

## Real-Time Updates Architecture (SSE)

### Overview

The system implements Server-Sent Events (SSE) for real-time workflow progress updates, eliminating the need for frontend polling.

### Architecture Pattern: Hybrid LangGraph + Redis

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Execution                        │
│                                                              │
│  LangGraph.astream() ──┐                                    │
│         │              │                                     │
│         ▼              ▼                                     │
│   Node Outputs    Redis Sync                                │
│         │              │                                     │
│         │              ▼                                     │
│         │         Redis State                               │
│         │              │                                     │
│         │              │                                     │
│         ▼              ▼                                     │
│   Final State    SSE Polling ──────► Frontend Updates       │
└─────────────────────────────────────────────────────────────┘
```

### Why Hybrid Approach?

**Problem**: LangGraph state is in-memory, SSE endpoint needs persistent access.

**Solution**: Dual-path architecture:
1. **LangGraph Streaming**: Real-time node outputs during execution
2. **Redis Sync**: State persisted after each node for SSE access
3. **SSE Polling**: Separate endpoint polls Redis every 500ms

**Benefits**:
- ✅ Real-time updates during execution
- ✅ State accessible after execution completes
- ✅ Supports workflow pause/resume
- ✅ Minimal overhead for POC

### Implementation Details

**Backend SSE Endpoint** (`backend/app/api/orchestration.py`):
```python
@router.get("/projects/{project_id}/workflow/stream")
async def stream_workflow_state(project_id: str):
    """Stream workflow state updates via SSE."""
    
    async def event_generator():
        last_version = -1
        last_phase = None
        
        while True:
            # Poll Redis state every 500ms
            state = await redis_client.get_state(project_id)
            
            if state:
                current_version = state.get("state_version", 0)
                current_phase = state.get("phase")
                
                # Send state_update event on version change
                if current_version > last_version:
                    yield {
                        "event": "state_update",
                        "data": json.dumps(state)
                    }
                    last_version = current_version
                
                # Send phase_transition event on phase change
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
            
            await asyncio.sleep(0.5)
    
    return EventSourceResponse(event_generator())
```

**Frontend SSE Hook** (`frontend/src/hooks/useWorkflowSSE.js`):
```javascript
const useWorkflowSSE = (projectId) => {
  const [state, setState] = useState(null);
  const [lastPhase, setLastPhase] = useState(null);
  
  useEffect(() => {
    const eventSource = new EventSource(
      `/api/projects/${projectId}/workflow/stream`
    );
    
    eventSource.addEventListener('state_update', (event) => {
      const newState = JSON.parse(event.data);
      setState(newState);
    });
    
    eventSource.addEventListener('phase_transition', (event) => {
      const transition = JSON.parse(event.data);
      console.log(`Phase: ${transition.from} → ${transition.to}`);
      setLastPhase(transition.to);
    });
    
    return () => eventSource.close();
  }, [projectId]);
  
  return { state, lastPhase };
};
```

**State Synchronization** (`backend/app/orchestration/workflow.py`):
```python
async def execute_workflow(self, project_id: str) -> Dict[str, Any]:
    """Execute workflow with Redis sync."""
    
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

### Event Types

| Event | Trigger | Data | Purpose |
|-------|---------|------|---------|
| `state_update` | State version changes | Full state object | Update UI with latest state |
| `phase_transition` | Phase changes | from, to, timestamp | Show phase progression |

### Performance Characteristics

- **Polling Interval**: 500ms (configurable)
- **Latency**: <1 second for state updates
- **Overhead**: Minimal Redis reads (cached in memory)
- **Connection**: Long-lived HTTP connection per client

### Error Handling

**Connection Loss**:
- Frontend automatically reconnects
- State preserved in Redis
- No data loss

**Redis Unavailable**:
- Workflow continues (in-memory state)
- SSE returns empty until Redis recovers
- Graceful degradation

### Future Enhancements

For production deployment:
1. **WebSockets**: Replace SSE for bidirectional communication
2. **Redis Pub/Sub**: Push-based updates instead of polling
3. **Connection Pooling**: Manage multiple SSE connections efficiently
4. **Compression**: Compress large state objects
5. **Selective Updates**: Send only changed fields, not full state

## Security Considerations

1. **Credentials Management**: All API keys in environment variables
2. **Access Control**: Bearer token authentication for MCP
3. **Data Privacy**: No persistent storage of sensitive data in POC
4. **Audit Trail**: Complete changelog of all state modifications
5. **Input Validation**: Pydantic models for all inputs
6. **SSE Security**: Project-scoped streams, no cross-project access

## Scalability Considerations (Future)

While this is a POC, the architecture supports future scaling:

1. **Horizontal Scaling**: Stateless agents can run in parallel
2. **State Persistence**: Replace in-memory with distributed store
3. **Queue-Based**: Add message queue for async processing
4. **Caching**: Add Redis for frequently accessed data
5. **Load Balancing**: Multiple API instances behind load balancer

## Success Metrics

1. **Functional**: Complete workflow from ingestion to plan
2. **Quality**: High confidence scores on extracted facts
3. **Traceability**: Every decision traceable to source
4. **Performance**: End-to-end execution < 5 minutes
5. **Reliability**: Successful fallback on provider failure

## Next Steps

Refer to phase-specific documents:
- [Phase 1: Foundation](./01-phase1-foundation.md)
- [Phase 2: MCP Connector](./02-phase2-mcp-connector.md)
- [Phase 3: Orchestration](./03-phase3-orchestration.md)
- [Phase 4: Core Agents](./04-phase4-core-agents.md)
- [Phase 5: Intake & Review](./05-phase5-intake-review.md)
- [Phase 6: Migration Planning](./06-phase6-migration-planning.md)
- [Phase 7: Frontend UI](./07-phase7-frontend.md)
- [Phase 8: Testing](./08-phase8-testing.md)