# Agent Details - Complete Reference

## Table of Contents
1. [Agent Architecture](#agent-architecture)
2. [Context Retrieval Agent](#context-retrieval-agent)
3. [Extraction Agent](#extraction-agent)
4. [Questionnaire Agent](#questionnaire-agent)
5. [Supervisor](#supervisor)
6. [Agent Communication](#agent-communication)

---

## Agent Architecture

### Common Agent Pattern

All agents follow the same interface:

```python
class SomeAgent:
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """Initialize agent with optional LLM provider"""
        self.agent_name = "some_agent"
        self.llm = llm_provider
    
    @trace_operation("some_agent", run_type="chain", tags=["agent"])
    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute agent logic.
        
        Args:
            state: Current workflow state (read-only)
            
        Returns:
            State patch (only changed fields)
        """
        # 1. Validate input
        project_id = state.get("project_id")
        if not project_id:
            raise ValueError("project_id required")
        
        # 2. Initialize LLM if needed
        if self.llm is None:
            self.llm = await get_provider()
        
        # 3. Do work
        result = await self._do_work(state)
        
        # 4. Return patch (not full state!)
        return {
            "new_field": result,
            "phase": "next_phase",
            "last_committed_by": self.agent_name,
            "last_committed_at": datetime.utcnow().isoformat()
        }
```

### Key Principles

1. **Read-Only State**: Agents receive state as input but don't modify it directly
2. **Return Patches**: Agents return only changed fields, not full state
3. **No Side Effects**: Agents don't call other agents or modify external state
4. **Error Handling**: Agents catch errors and return error patches
5. **Tracing**: All agents use `@trace_operation` for LangSmith

---

## Context Retrieval Agent

**File**: `backend/app/agents/context_retrieval_agent.py`

### Purpose

Gather all relevant documents from multiple sources with automatic fallback.

### Multi-Source Strategy

```
┌─────────────────────────────────────────────────────────┐
│  Source Priority                                        │
│                                                          │
│  1. MCP (IBM Context Studio) ─────► Primary            │
│     ↓ (if fails or empty)                              │
│  2. Uploaded Documents (Qdrant) ──► Fallback           │
│     ↓ (if fails or empty)                              │
│  3. Cached Context ───────────────► Last Resort        │
│     ↓ (if all fail)                                    │
│  4. Error ─────────────────────────► Workflow stops    │
└─────────────────────────────────────────────────────────┘
```

### Input Requirements

```python
{
    "project_id": "pintu-test",  # Required
    "mcp_request_profile": {     # Optional
        "profile_name": "context_retrieval_profile",
        "query": "migration context"
    }
}
```

### Execution Flow

```python
async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute multi-source context retrieval.
    
    Flow:
    1. Validate project_id
    2. Try MCP retrieval
    3. If MCP fails, try uploaded documents
    4. If both fail, try cached context
    5. If all fail, return error
    6. Normalize documents
    7. Return patch
    """
    
    # Step 1: Validate
    project_id = state.get("project_id")
    if not project_id:
        return self._error_response(state, "project_id required")
    
    # Step 2: Try MCP
    context_pack, source = await self._try_mcp_retrieval(project_id, state)
    sources_tried = [source]
    
    # Step 3: Try uploaded documents
    if context_pack is None:
        context_pack, source = await self._try_uploaded_documents(project_id, state)
        sources_tried.append(source)
    
    # Step 4: Try cached context
    if context_pack is None:
        context_pack, source = await self._try_cached_context(project_id, state)
        sources_tried.append(source)
    
    # Step 5: All failed
    if context_pack is None:
        return self._error_response(
            state,
            f"All sources failed: {', '.join(sources_tried)}"
        )
    
    # Step 6: Normalize
    normalized_docs = self._normalize_context_pack(context_pack)
    
    # Step 7: Return patch
    return {
        "context_pack": self._context_pack_to_dict(context_pack),
        "normalized_docs": normalized_docs,
        "phase": "extraction",
        "trace_metadata": {
            **state.get("trace_metadata", {}),
            "context_retrieval": {
                "documents_retrieved": len(normalized_docs),
                "source_used": sources_tried[-1],
                "sources_tried": sources_tried,
                "timestamp": datetime.utcnow().isoformat()
            }
        },
        "last_committed_by": self.agent_name,
        "last_committed_at": datetime.utcnow().isoformat()
    }
```

### Source Methods

#### 1. MCP Retrieval

```python
async def _try_mcp_retrieval(
    self,
    project_id: str,
    state: Dict[str, Any]
) -> tuple[Optional[ContextPack], str]:
    """
    Try to retrieve from MCP (IBM Context Studio).
    
    Returns:
        (ContextPack or None, source_name)
    """
    try:
        # Get profile
        profile = get_profile(ProfileType.CONTEXT_RETRIEVAL)
        
        # Initialize connector
        connector = MCPConnector(
            gateway_url=settings.mcp_gateway_url,
            gateway_token=settings.mcp_gateway_token,
            api_key=settings.mcp_api_key
        )
        
        # Execute retrieval
        context_pack = await connector.retrieve(
            profile=profile,
            project_id=project_id,
            query=state.get("mcp_request_profile", {}).get("query")
        )
        
        await connector.close()
        
        if context_pack and len(context_pack.documents) > 0:
            return context_pack, "mcp"
        
        return None, "mcp (empty)"
        
    except Exception as e:
        logger.warning(f"MCP retrieval failed: {e}")
        return None, f"mcp (error: {str(e)})"
```

#### 2. Uploaded Documents

```python
async def _try_uploaded_documents(
    self,
    project_id: str,
    state: Dict[str, Any]
) -> tuple[Optional[ContextPack], str]:
    """
    Try to retrieve uploaded documents from Qdrant.
    
    Returns:
        (ContextPack or None, source_name)
    """
    try:
        # Initialize Qdrant
        qdrant_store = QdrantStore()
        await qdrant_store.initialize()
        
        # List documents
        collection_name = f"project_{project_id}"
        documents = await qdrant_store.list_documents(collection_name)
        
        if not documents:
            return None, "uploaded_documents (empty)"
        
        # Convert to ContextPack
        context_pack = ContextPack(
            documents=[
                Document(
                    id=doc.get("id", "unknown"),
                    title=doc.get("metadata", {}).get("source_file", "Untitled"),
                    content=doc.get("text", ""),
                    source_type="uploaded",
                    metadata=doc.get("metadata", {})
                )
                for doc in documents
            ],
            total_count=len(documents),
            metadata={"source": "uploaded_documents"}
        )
        
        return context_pack, "uploaded_documents"
        
    except Exception as e:
        logger.warning(f"Uploaded documents retrieval failed: {e}")
        return None, f"uploaded_documents (error: {str(e)})"
```

#### 3. Cached Context

```python
async def _try_cached_context(
    self,
    project_id: str,
    state: Dict[str, Any]
) -> tuple[Optional[ContextPack], str]:
    """
    Try to retrieve cached context from previous runs.
    
    Returns:
        (ContextPack or None, source_name)
    """
    try:
        # Check if state already has context_pack
        existing_context = state.get("context_pack")
        if existing_context and existing_context.get("documents"):
            # Reconstruct ContextPack
            context_pack = ContextPack(
                documents=[
                    Document(**doc)
                    for doc in existing_context["documents"]
                ],
                total_count=existing_context.get("total_count", 0),
                metadata=existing_context.get("metadata", {})
            )
            return context_pack, "cached_context"
        
        return None, "cached_context (empty)"
        
    except Exception as e:
        logger.warning(f"Cached context retrieval failed: {e}")
        return None, f"cached_context (error: {str(e)})"
```

### Output Format

```python
{
    "context_pack": {
        "documents": [
            {
                "id": "doc_1",
                "title": "Application Architecture",
                "content": "The application uses...",
                "source_type": "uploaded",
                "metadata": {
                    "source_file": "architecture.pdf",
                    "project_id": "pintu-test"
                }
            },
            # ... 28 more documents
        ],
        "total_count": 29,
        "metadata": {
            "source": "uploaded_documents"
        }
    },
    "normalized_docs": [
        {
            "id": "doc_1",
            "title": "Application Architecture",
            "content": "The application uses...",
            "source_type": "uploaded",
            "metadata": {...}
        },
        # ... 28 more
    ],
    "phase": "extraction",
    "trace_metadata": {
        "context_retrieval": {
            "documents_retrieved": 29,
            "source_used": "uploaded_documents",
            "sources_tried": ["mcp (empty)", "uploaded_documents"],
            "timestamp": "2026-05-27T19:00:00Z"
        }
    },
    "last_committed_by": "context_retrieval_agent",
    "last_committed_at": "2026-05-27T19:00:00Z"
}
```

---

## Extraction Agent

**File**: `backend/app/agents/extraction_agent.py`

### Purpose

Extract structured technical facts from unstructured documents using LLM.

### Input Requirements

```python
{
    "project_id": "pintu-test",  # Required
    "normalized_docs": [         # Required (from context retrieval)
        {
            "id": "doc_1",
            "title": "Architecture",
            "content": "The app uses Node.js...",
            "metadata": {"project_id": "pintu-test"}
        },
        # ... more docs
    ]
}
```

### Execution Flow

```python
async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract facts from documents.
    
    Flow:
    1. Validate project_id and documents
    2. Initialize LLM provider
    3. Build extraction prompt
    4. Call LLM with structured output
    5. Process extraction result
    6. Calculate confidence scores
    7. Map facts to evidence
    8. Return patch
    """
    
    try:
        # Step 1: Validate
        project_id = state.get("project_id")
        if not project_id:
            raise ValueError("project_id required")
        
        normalized_docs = state.get("normalized_docs", [])
        if not normalized_docs:
            raise ValueError("No documents to extract from")
        
        # Validate documents belong to correct project
        for idx, doc in enumerate(normalized_docs):
            doc_project = doc.get("metadata", {}).get("project_id")
            if doc_project and doc_project != project_id:
                raise ValueError(
                    f"Document {idx} belongs to project {doc_project}, "
                    f"not {project_id}"
                )
        
        # Step 2: Initialize LLM
        if self.llm is None:
            self.llm = await get_provider(prefer_primary=True)
        
        # Step 3: Build prompt
        prompt = self._build_extraction_prompt(normalized_docs)
        
        # Step 4: Call LLM
        extraction_result = await self.llm.generate_structured(
            prompt=prompt,
            schema=self._get_extraction_schema(),
            system_prompt="You are a technical analyst...",
            temperature=0.1,
            metadata={
                "agent": self.agent_name,
                "task": "fact_extraction",
                "document_count": len(normalized_docs)
            }
        )
        
        # Step 5: Process result
        extracted_facts = self._process_extraction(
            extraction_result,
            normalized_docs
        )
        
        # Step 6: Calculate confidence
        confidence_scores = self._calculate_confidence_scores(extracted_facts)
        
        # Step 7: Map to evidence
        evidence_map = self._map_facts_to_evidence(
            extracted_facts,
            normalized_docs
        )
        
        # Step 8: Return patch
        total_facts = sum(len(facts) for facts in extracted_facts.values())
        avg_confidence = (
            sum(confidence_scores.values()) / len(confidence_scores)
            if confidence_scores else 0
        )
        
        return {
            "extracted_facts": extracted_facts,
            "confidence_scores": confidence_scores,
            "evidence_map": evidence_map,
            "phase": "questionnaire",
            "trace_metadata": {
                **state.get("trace_metadata", {}),
                "extraction": {
                    "facts_extracted": total_facts,
                    "avg_confidence": avg_confidence,
                    "categories": list(extracted_facts.keys()),
                    "timestamp": datetime.utcnow().isoformat()
                }
            },
            "last_committed_by": self.agent_name,
            "last_committed_at": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"[{self.agent_name}] Error: {str(e)}", exc_info=True)
        return {
            "phase": "error",
            "last_error": f"Fact extraction failed: {str(e)}",
            "error_log": [
                *state.get("error_log", []),
                {
                    "agent": self.agent_name,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            ],
            "last_committed_by": self.agent_name,
            "last_committed_at": datetime.utcnow().isoformat()
        }
```

### Extraction Categories

The agent extracts facts in these categories:

1. **Technical Stack**
   - Programming languages and versions
   - Frameworks and libraries
   - Runtime environments
   - Build tools

2. **Dependencies**
   - Internal services and APIs
   - External APIs and integrations
   - Databases and data stores
   - Message queues and event systems

3. **Runtime Configuration**
   - Environment variables
   - Configuration files
   - Feature flags
   - Secrets management

4. **Deployment Strategy**
   - Current deployment method
   - CI/CD pipeline
   - Infrastructure (servers, containers, etc.)
   - Scaling approach

5. **Architectural Decisions**
   - Design patterns used
   - Architectural style (monolith, microservices, etc.)
   - Communication patterns
   - Data flow

6. **Security & Compliance**
   - Authentication methods
   - Authorization approach
   - Data encryption
   - Compliance requirements (GDPR, HIPAA, etc.)

7. **Known Risks**
   - Technical debt
   - Deprecated dependencies
   - Performance bottlenecks
   - Known issues

### Prompt Building

```python
def _build_extraction_prompt(self, normalized_docs: List[Dict[str, Any]]) -> str:
    """Build extraction prompt from documents."""
    
    # Combine document chunks (limit to avoid token overflow)
    context_parts = []
    total_chars = 0
    max_chars = 15000
    
    for doc in normalized_docs[:10]:  # Limit to 10 documents
        doc_id = doc.get('id', 'unknown')
        doc_title = doc.get('title', 'Untitled')
        doc_content = doc.get('content', '')
        
        doc_text = f"Document: {doc_title}\n"
        doc_text += f"Source ID: {doc_id}\n"
        doc_text += f"Content:\n{doc_content[:2000]}\n"  # Limit per doc
        
        if total_chars + len(doc_text) > max_chars:
            break
        
        context_parts.append(doc_text)
        total_chars += len(doc_text)
    
    context_text = "\n---\n".join(context_parts)
    
    prompt = f"""You are a technical analyst extracting migration-relevant facts.

CONTEXT DOCUMENTS:
{context_text}

EXTRACT THE FOLLOWING INFORMATION:
[... detailed extraction instructions ...]

For each fact:
- Provide clear, specific statement
- Assign confidence score (0.0-1.0)
- Reference source document ID
- Quote supporting evidence
"""
    
    return prompt
```

### Output Format

```python
{
    "extracted_facts": {
        "technical_stack": [
            {
                "fact_id": "ts_001",
                "category": "language",
                "fact": "Application uses Node.js v14.17.0",
                "confidence": 0.95,
                "source_id": "doc_1",
                "evidence": "package.json specifies 'node': '14.17.0'"
            },
            # ... more facts
        ],
        "dependencies": [...],
        "deployment_strategy": [...],
        # ... other categories
    },
    "confidence_scores": {
        "ts_001": 0.95,
        "ts_002": 0.87,
        # ... all fact IDs
    },
    "evidence_map": {
        "ts_001": ["doc_1"],
        "ts_002": ["doc_1", "doc_3"],
        # ... all fact IDs
    },
    "phase": "questionnaire",
    "trace_metadata": {
        "extraction": {
            "facts_extracted": 45,
            "avg_confidence": 0.82,
            "categories": ["technical_stack", "dependencies", ...],
            "timestamp": "2026-05-27T19:01:00Z"
        }
    }
}
```

---

## Questionnaire Agent

**File**: `backend/app/agents/questionnaire_agent.py`

### Purpose

Identify information gaps and generate prioritized questions to fill those gaps.

### Input Requirements

```python
{
    "project_id": "pintu-test",  # Required
    "extracted_facts": {...},    # Required (from extraction)
    "confidence_scores": {...}   # Required (from extraction)
}
```

### Gap Detection

#### 1. Low Confidence Facts

Facts with confidence < 0.7:

```python
def _identify_low_confidence_facts(
    self,
    extracted_facts: Dict[str, List[Dict[str, Any]]],
    confidence_scores: Dict[str, float]
) -> List[Dict[str, Any]]:
    """Identify facts with confidence below threshold."""
    
    LOW_CONFIDENCE_THRESHOLD = 0.7
    low_confidence = []
    
    for category, facts in extracted_facts.items():
        for fact in facts:
            fact_id = fact.get("fact_id", "")
            confidence = confidence_scores.get(fact_id, 0.0)
            
            if confidence < LOW_CONFIDENCE_THRESHOLD:
                low_confidence.append({
                    **fact,
                    "confidence": confidence,
                    "gap_type": "low_confidence"
                })
    
    return low_confidence
```

#### 2. Missing Required Fields

Required fields that weren't extracted:

```python
REQUIRED_FIELDS = [
    "technical_stack.language",
    "technical_stack.framework",
    "dependencies.databases",
    "deployment_strategy.current_method",
    "security_compliance.authentication",
    "architectural_decisions.architecture_style"
]

def _identify_missing_fields(
    self,
    extracted_facts: Dict[str, List[Dict[str, Any]]]
) -> List[str]:
    """Identify required fields that are missing."""
    
    missing = []
    
    for required_field in REQUIRED_FIELDS:
        category, field = required_field.split(".", 1)
        
        # Check if category exists
        if category not in extracted_facts:
            missing.append(required_field)
            continue
        
        # Check if field exists in category
        facts = extracted_facts[category]
        field_found = any(
            field.lower() in fact.get("category", "").lower() or
            field.lower() in fact.get("fact", "").lower()
            for fact in facts
        )
        
        if not field_found:
            missing.append(required_field)
    
    return missing
```

### Question Generation

```python
async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """Generate questions for gaps."""
    
    # Identify gaps
    low_confidence_facts = self._identify_low_confidence_facts(
        extracted_facts,
        confidence_scores
    )
    missing_fields = self._identify_missing_fields(extracted_facts)
    
    # Build prompt
    prompt = self._build_questionnaire_prompt(
        extracted_facts,
        low_confidence_facts,
        missing_fields
    )
    
    # Generate questions using LLM
    questions_result = await self.llm.generate_structured(
        prompt=prompt,
        schema=self._get_question_schema(),
        system_prompt="You are a migration analyst...",
        temperature=0.3
    )
    
    # Process and prioritize
    questions = self._process_questions(questions_result)
    prioritized_questions = self._prioritize_questions(questions)
    
    return {
        "missing_questions": prioritized_questions,
        "question_priorities": {
            q["question_id"]: q["priority_score"]
            for q in prioritized_questions
        },
        "gap_analysis": {
            "low_confidence_facts": len(low_confidence_facts),
            "missing_fields": len(missing_fields),
            "total_gaps": len(low_confidence_facts) + len(missing_fields)
        },
        "phase": "intake_draft",
        "trace_metadata": {...}
    }
```

### Output Format

```python
{
    "missing_questions": [
        {
            "question_id": "q_001",
            "question": "What is the exact Node.js version used in production?",
            "category": "technical_stack",
            "priority": "HIGH",
            "priority_score": 0.95,
            "gap_type": "low_confidence",
            "related_fact_id": "ts_001",
            "rationale": "Current confidence is 0.65, need exact version for migration planning"
        },
        {
            "question_id": "q_002",
            "question": "Which database system is used?",
            "category": "dependencies",
            "priority": "HIGH",
            "priority_score": 0.90,
            "gap_type": "missing_field",
            "related_fact_id": null,
            "rationale": "Database information is required for migration strategy"
        },
        # ... more questions
    ],
    "question_priorities":  {
        "q_001": 0.95,
        "q_002": 0.90,
        # ...
    },
    "gap_analysis": {
        "low_confidence_facts": 5,
        "missing_fields": 3,
        "total_gaps": 8
    },
    "phase": "intake_draft"
}
```

---

## Supervisor

**File**: `backend/app/orchestration/supervisor.py`

### Purpose

Control workflow routing and phase transitions based on current state.

### Decision Tree

```python
async def decide_next_node(
    self,
    state: MigrationState
) -> SupervisorDecision:
    """
    Decide next node based on current state.
    
    Decision tree:
    1. INIT → context_retrieval
    2. CONTEXT_RETRIEVAL → extraction (if context exists, else retry)
    3. EXTRACTION → questionnaire (if facts exist, else retry)
    4. QUESTIONNAIRE → intake_draft
    5. INTAKE_DRAFT → human_review (if draft exists, else retry)
    6. HUMAN_REVIEW → migration_planning (if approved)
    7. MIGRATION_PLANNING → validation
    8. VALIDATION → complete
    9. ERROR → retry or fail
    """
    
    current_phase = WorkflowPhase(state["phase"])
    
    # Check for errors
    if current_phase == WorkflowPhase.ERROR:
        return await self._handle_error(state)
    
    # Normal flow
    if current_phase == WorkflowPhase.INIT:
        return SupervisorDecision(
            next_node="context_retrieval",
            next_phase=WorkflowPhase.CONTEXT_RETRIEVAL,
            reason="Starting workflow: retrieve context"
        )
    
    elif current_phase == WorkflowPhase.CONTEXT_RETRIEVAL:
        if not state.get("context_pack"):
            return SupervisorDecision(
                next_node="context_retrieval",
                next_phase=WorkflowPhase.CONTEXT_RETRIEVAL,
                reason="Retry: context not retrieved"
            )
        return SupervisorDecision(
            next_node="extraction",
            next_phase=WorkflowPhase.EXTRACTION,
            reason="Context retrieved: extract facts"
        )
    
    elif current_phase == WorkflowPhase.EXTRACTION:
        if not state.get("extracted_facts"):
            return SupervisorDecision(
                next_node="extraction",
                next_phase=WorkflowPhase.EXTRACTION,
                reason="Retry: facts not extracted"
            )
        return SupervisorDecision(
            next_node="questionnaire",
            next_phase=WorkflowPhase.QUESTIONNAIRE,
            reason="Facts extracted: generate questions"
        )
    
    # ... continues for all phases
```

### Retry Logic

```python
async def _handle_error(self, state: MigrationState) -> SupervisorDecision:
    """Handle error state with retry logic."""
    
    error_log = state.get("error_log", [])
    last_error = state.get("last_error", "")
    
    # Count retries for current phase
    current_phase_errors = [
        e for e in error_log
        if e.get("phase") == state["phase"]
    ]
    
    MAX_RETRIES = 3
    
    if len(current_phase_errors) >= MAX_RETRIES:
        return SupervisorDecision(
            next_node="END",
            next_phase=WorkflowPhase.ERROR,
            reason=f"Max retries exceeded: {last_error}"
        )
    
    # Retry current phase
    return SupervisorDecision(
        next_node=state["phase"],
        next_phase=WorkflowPhase(state["phase"]),
        reason=f"Retry after error: {last_error}"
    )
```

---

## Agent Communication

### How Agents Communicate

Agents **DO NOT** communicate directly. They communicate through shared state:

```
Agent A → Returns Patch → LangGraph Merges → State Updated
                                                    ↓
Agent B ← Reads State ← LangGraph Passes ← State Updated
```

### Example Flow

```python
# Context Retrieval Agent
async def execute(self, state):
    docs = await self.retrieve_docs(state["project_id"])
    return {
        "normalized_docs": docs,  # Adds to state
        "phase": "extraction"
    }

# State after merge
state = {
    "project_id": "test",
    "normalized_docs": [doc1, doc2, ...],  # NEW
    "phase": "extraction"  # UPDATED
}

# Extraction Agent (next)
async def execute(self, state):
    docs = state["normalized_docs"]  # Reads from state
    facts = await self.extract(docs)
    return {
        "extracted_facts": facts,  # Adds to state
        "phase": "questionnaire"
    }

# State after merge
state = {
    "project_id": "test",
    "normalized_docs": [doc1, doc2, ...],  # Still here
    "extracted_facts": {...},  # NEW
    "phase": "questionnaire"  # UPDATED
}
```

### No Direct Calls

**DON'T**:
```python
# Agent A calling Agent B directly
class AgentA:
    async def execute(self, state):
        result = await self.agent_b.execute(state)  # ❌ WRONG
        return result
```

**DO**:
```python
# Agent A returns patch, LangGraph routes to Agent B
class AgentA:
    async def execute(self, state):
        result = await self.do_work(state)
        return {
            "field_a": result,
            "phase": "next_phase"  # Supervisor routes to Agent B
        }
```

---

## Next Steps

- [04-data-structures.md](./04-data-structures.md) - Detailed data formats
- [05-execution-flow.md](./05-execution-flow.md) - Step-by-step execution
- [06-error-handling.md](./06-error-handling.md) - Error handling and retries