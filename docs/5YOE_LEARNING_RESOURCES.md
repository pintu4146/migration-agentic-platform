# 5 Years of Experience (5 YOE) Backend Learning Resources

**IBM Migration Copilot - Advanced Architecture Guide**

This document provides interview-ready, enterprise-grade patterns from the actual codebase. Designed for system design interviews, architecture decisions, and production systems.

---

## Table of Contents

1. [State Management with LangGraph](#state-management)
2. [Provider Pattern & Dependency Injection](#provider-pattern)
3. [Error Handling & Recovery](#error-handling)
4. [FastAPI Async Patterns](#fastapi-patterns)
5. [Testing Strategies](#testing)
6. [SOLID Principles in Practice](#solid)
7. [Performance & Scaling Considerations](#performance)
8. [Interview Q&A](#interview-qa)

---

## State Management with LangGraph {#state-management}

### Problem Statement

Multi-agent systems need to coordinate state updates safely:
- Agent A reads state version 5
- Agent B updates state to version 6
- Agent A tries to update with data from version 5 → Conflict!

### Solution: Immutable, Versioned State

**File:** `backend/app/orchestration/state.py`

```python
from typing import TypedDict, Annotated, List, Dict, Any

def merge_lists(left: List[Any], right: List[Any]) -> List[Any]:
    """Reducer: append right list to left list"""
    if left is None: left = []
    if right is None: right = []
    if not isinstance(left, list): left = [left] if left else []
    if not isinstance(right, list): right = [right] if right else []
    return left + right

def merge_dicts(left: Optional[Dict[str, Any]], right: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Reducer: shallow merge with right-precedence"""
    if right is None: return left
    if left is None: return right
    return {**left, **right}

class MigrationState(TypedDict):
    """Immutable workflow state with version control"""
    # Identity
    project_id: str
    state_version: int  # Optimistic locking
    phase: WorkflowPhase
    created_at: str
    updated_at: str
    
    # Annotated fields with custom reducers
    normalized_docs: Annotated[List[Dict[str, Any]], merge_lists]
    missing_questions: Annotated[List[Dict[str, Any]], merge_lists]
    trace_metadata: Annotated[Dict[str, Any], merge_dicts]
    state_changelog: Annotated[List[StateChangelogEntry], merge_lists]
```

### How Annotated Reducers Work

When LangGraph merges state updates:

```python
# Current state (from Redis)
state_v5 = {
    'state_version': 5,
    'normalized_docs': [{'id': 1, 'text': 'doc1'}],
    'trace_metadata': {'init': {'timestamp': '...'}}
}

# Agent returns a patch
patch = {
    'state_version': 6,
    'normalized_docs': [{'id': 2, 'text': 'doc2'}],  # merge_lists applied
    'trace_metadata': {'extraction': {'facts': 42}}  # merge_dicts applied
}

# LangGraph applies reducers
merged = {
    'state_version': 6,
    'normalized_docs': [{'id': 1, ...}, {'id': 2, ...}],  # Lists concatenated
    'trace_metadata': {  # Dicts merged, extraction key added
        'init': {'timestamp': '...'},
        'extraction': {'facts': 42}
    }
}
```

### Optimistic Locking Pattern

**File:** `backend/app/orchestration/state_manager.py`

```python
async def commit_state(self, project_id: str, patch: Dict[str, Any], 
                      committed_by: str, reason: str) -> MigrationState:
    """Commit with optimistic locking and changelog"""
    async with self._lock:  # asyncio.Lock for mutual exclusion
        current = await self.get_state(project_id)
        read_version = current['state_version']
        
        # Critical: Check version matches
        if current['state_version'] != read_version:
            raise StateTransactionError(
                f"Version mismatch: {read_version} != {current['state_version']}"
            )
        
        # Validate (don't allow protected fields)
        self._validate_patch(patch)
        
        # Create changelog entry
        changelog = {
            'version': read_version + 1,
            'patch': patch,
            'committed_by': committed_by,
            'committed_at': datetime.utcnow().isoformat(),
            'previous_phase': current['phase'],
            'new_phase': patch.get('phase', current['phase']),
            'description': reason
        }
        
        # Merge state
        updated = {
            **current,
            **patch,
            'state_version': read_version + 1,
            'state_changelog': [*current['state_changelog'], changelog]
        }
        
        # Write to Redis (atomic)
        await self._save_to_redis(project_id, updated)
        
        return updated
```

### Why This Works

- **Immutability:** Agents cannot modify state directly—they propose patches
- **Versioning:** Each commit increments version, detects lost updates
- **Audit Trail:** Changelog logs every change with reason and timestamp
- **Replay:** Can restore any historical state from changelog
- **Lock-free reads:** Multiple agents read simultaneously (version check at write time)

### Interview Q&A

**Q: Why use optimistic locking instead of pessimistic (global lock)?**

A: Optimistic locking is better for read-heavy workloads (agents read state frequently, update rarely).
- Pessimistic: Hold lock during entire agent processing (slow, bottleneck)
- Optimistic: Only check at commit time (detect conflicts, retry if needed)

**Q: What if two agents write at the same version?**

A: Both update concurrently:
- Agent A reads version 5, processes for 2 seconds, tries to write
- Agent B reads version 5, processes for 1 second, writes first → version becomes 6
- Agent A's write fails (version mismatch) → Agent A must retry with version 6

**Q: How do you handle retry loops?**

A: Track `retry_count` in state:
```python
if retry_count >= max_retries:
    return {'phase': WorkflowPhase.ERROR, 'last_error': 'Max retries exceeded'}
return {'retry_count': retry_count + 1, 'phase': WorkflowPhase.ERROR}
```

---

## Provider Pattern & Dependency Injection {#provider-pattern}

### Problem: Tight Coupling

```python
# ❌ Bad: Hardcoded dependency
class ExtractionAgent:
    def __init__(self):
        self.llm = OpenAIClient(api_key=OPENAI_KEY)  # Tightly coupled!
    
    async def extract_facts(self, text):
        return await self.llm.generate(text)
```

Issues:
- Can't test without real OpenAI API calls
- If OpenAI is down, extraction fails immediately (no fallback)
- Adding Gemini support requires code change

### Solution: Abstract Interface + Factory

**File:** `backend/app/providers/base.py`

```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    """Abstract interface"""
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> ProviderResponse:
        pass
    
    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate JSON matching schema"""
        pass
    
    @abstractmethod
    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]]
    ) -> ProviderResponse:
        """Function calling capability"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass
```

**File:** `backend/app/providers/factory.py`

```python
class ProviderFactory:
    """Factory with circuit breaker"""
    
    def __init__(self):
        self.primary_provider: Optional[LLMProvider] = None
        self.fallback_provider: Optional[LLMProvider] = None
        self.primary_status = ProviderStatus.HEALTHY
        self.fallback_status = ProviderStatus.HEALTHY
        self.failure_count = 0
    
    async def initialize(self):
        """Initialize both providers"""
        try:
            self.primary_provider = self._create_provider(settings.primary_provider)
            is_healthy = await self.primary_provider.health_check()
            self.primary_status = ProviderStatus.HEALTHY if is_healthy else ProviderStatus.UNAVAILABLE
        except Exception as e:
            logger.error(f"Primary init failed: {e}")
            self.primary_status = ProviderStatus.UNAVAILABLE
        
        # Initialize fallback similarly...
    
    async def get_provider(self, prefer_primary: bool = True) -> LLMProvider:
        """Get available provider with automatic fallback"""
        # Try primary if healthy
        if (prefer_primary and self.primary_provider 
            and self.primary_status == ProviderStatus.HEALTHY):
            return self.primary_provider
        
        # Try fallback
        if (self.fallback_provider 
            and self.fallback_status == ProviderStatus.HEALTHY):
            return self.fallback_provider
        
        # Try primary even if degraded
        if (self.primary_provider 
            and self.primary_status != ProviderStatus.UNAVAILABLE):
            return self.primary_provider
        
        raise RuntimeError("No providers available")
    
    async def handle_provider_failure(self, provider: LLMProvider) -> None:
        """Circuit breaker: mark as degraded/unavailable"""
        self.failure_count += 1
        if self.failure_count >= self.max_failures:
            if provider == self.primary_provider:
                self.primary_status = ProviderStatus.UNAVAILABLE
            else:
                self.fallback_status = ProviderStatus.UNAVAILABLE
```

### How Agents Use This

**File:** `backend/app/agents/extraction_agent.py`

```python
class ExtractionAgent:
    def __init__(self, llm: Optional[LLMProvider] = None):
        self.llm = llm  # Injected dependency
    
    async def execute(self, state: MigrationState) -> Dict[str, Any]:
        try:
            # Lazy initialization if needed
            if self.llm is None:
                self.llm = await get_provider_factory().get_provider()
            
            # Use LLM
            facts = await self.llm.generate_structured(
                prompt=f"Extract facts from: {state['context_pack']}",
                schema=FACTS_SCHEMA
            )
            
            return {
                'extracted_facts': facts,
                'confidence_scores': self._compute_confidence(facts)
            }
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            await get_provider_factory().handle_provider_failure(self.llm)
            raise
```

### Testing with Mocks

```python
# ✓ Easy to test with mock
mock_llm = AsyncMock(spec=LLMProvider)
mock_llm.generate_structured.return_value = {'facts': [...]}

agent = ExtractionAgent(llm=mock_llm)
result = await agent.execute(test_state)

assert result['extracted_facts'] == {'facts': [...]}
```

### Circuit Breaker States

```
HEALTHY ──(failure)──> DEGRADED ──(max_failures)──> UNAVAILABLE
   ▲                                                       │
   │                                                       │
   └────────────(success resets counter)──────────────────┘
```

- **HEALTHY:** Use normally
- **DEGRADED:** Track failures, still attempt
- **UNAVAILABLE:** Fast-fail, don't retry

---

## Error Handling & Recovery {#error-handling}

### Exception Hierarchy

```python
# Application layer
class StateTransactionError(Exception):
    """State version mismatch, conflict"""
    pass

class StateValidationError(Exception):
    """Invalid state update attempt"""
    pass

class ProviderFailureError(Exception):
    """All LLM providers exhausted"""
    pass

class MCPConnectionError(Exception):
    """MCP gateway unreachable"""
    pass
```

### FastAPI Exception Handlers

**File:** `backend/app/main.py`

```python
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors (422)"""
    logger.warning(f"Validation error: {exc.errors()}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "detail": str(exc.errors())
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unhandled exceptions (500)"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            # Don't leak details in production
            "detail": str(exc) if settings.environment != "production" else None
        }
    )
```

### Retry with Exponential Backoff

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),  # 2s, 4s, 10s
    retry=retry_if_exception_type(ConnectionError),
    before_sleep=before_sleep_log(logger, logging.INFO)
)
async def fetch_from_mcp(profile: str):
    """Retry on transient failures"""
    # Attempt 1: immediate fail → wait 2-4s
    # Attempt 2: immediate fail → wait 4-8s
    # Attempt 3: immediate fail → raise
    pass
```

### Error Recovery Strategies

**1. Fail-fast for permanent errors:**
```python
try:
    response = await provider.generate(prompt)
except RequestValidationError as e:
    # Bad request—don't retry
    raise
except ConnectionError as e:
    # Transient—retry
    raise
```

**2. State rollback on failure:**
```python
# Before making risky change
checkpoint = deepcopy(current_state)

try:
    # Execute
    updated = await risky_operation(state)
except Exception as e:
    # Rollback
    await state_manager.restore_checkpoint(project_id, checkpoint)
    raise
```

**3. Partial success handling:**
```python
# If extraction gets 8 of 10 facts, don't fail—mark as incomplete
return {
    'extracted_facts': {
        'service_endpoints': [...],  # Found
        'database_config': None,  # Not found
    },
    'confidence_scores': {...},
    'review_flags': ['Missing database configuration']
}
```

---

## FastAPI Async Patterns {#fastapi-patterns}

### Lifespan Management (Startup/Shutdown)

**File:** `backend/app/main.py`

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    
    # ===== STARTUP =====
    logger.info("Starting Migration Copilot API")
    
    # Initialize global provider factory
    global provider_factory
    provider_factory = ProviderFactory()
    await provider_factory.initialize()  # Must await!
    logger.info("Provider factory initialized")
    
    # Perform health checks
    try:
        if provider_factory.primary_provider:
            primary_health = await provider_factory.primary_provider.health_check()
            logger.info(f"Primary: {primary_health}")
    except Exception as e:
        logger.error(f"Health check failed: {e}")
    
    logger.info("Startup complete")
    
    yield  # App is now running
    
    # ===== SHUTDOWN =====
    logger.info("Shutting down Migration Copilot API")
    provider_factory = None
    logger.info("Shutdown complete")

app = FastAPI(
    title="Migration Copilot API",
    lifespan=lifespan,  # Attach lifespan
    docs_url="/docs" if settings.environment != "production" else None
)
```

### Async Context Managers

```python
class RedisClient:
    async def __aenter__(self):
        """Connect to Redis"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close Redis connection"""
        await self.close()
    
    async def get(self, key: str):
        """Get value from Redis"""
        return await self.redis.get(key)

# Usage
async with RedisClient() as redis:
    value = await redis.get("state:project-123")
```

### Streaming Responses (SSE)

**File:** `backend/app/api/orchestration.py`

```python
@router.get("/stream/{project_id}")
async def stream_workflow_updates(project_id: str):
    """Server-Sent Events stream for real-time updates"""
    
    async def event_generator():
        """Generate SSE events"""
        while True:
            try:
                # Get current state
                state = await state_manager.get_state(project_id)
                
                # Send state_update event
                yield f"event: state_update\n"
                yield f"data: {json.dumps(state.model_dump())}\n\n"
                
                # Check for phase transition
                if state['phase'] != previous_phase:
                    transition = {
                        'from_phase': previous_phase,
                        'to_phase': state['phase'],
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    yield f"event: phase_transition\n"
                    yield f"data: {json.dumps(transition)}\n\n"
                    previous_phase = state['phase']
                
                # Send error if any
                if state['last_error']:
                    yield f"event: error\n"
                    yield f"data: {json.dumps({'error': state['last_error']})}\n\n"
                
                # Check if complete
                if state['phase'] == WorkflowPhase.COMPLETE:
                    break
                
                # Poll interval
                await asyncio.sleep(1)
            
            except Exception as e:
                logger.error(f"SSE error: {e}")
                yield f"event: error\n"
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
                break
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

### Dependency Injection with Annotations

```python
from typing import Annotated
from fastapi import Depends

async def get_state_manager() -> StateManager:
    """Dependency provider"""
    if not hasattr(get_state_manager, 'instance'):
        get_state_manager.instance = StateManager()
    return get_state_manager.instance

@app.post("/workflow/execute")
async def execute_workflow(
    project_id: str,
    state_manager: Annotated[StateManager, Depends(get_state_manager)]
):
    """Dependency injection: state_manager injected by FastAPI"""
    state = await state_manager.get_state(project_id)
    return {"state": state}
```

---

## Testing Strategies {#testing}

### Environment Isolation

**File:** `backend/tests/conftest.py`

```python
import os
import sys
import pytest
from unittest.mock import AsyncMock, Mock

# CRITICAL: Set env BEFORE importing app
os.environ['ENVIRONMENT'] = 'test'
os.environ['OPENAI_API_KEY'] = 'test-key'
os.environ['GEMINI_API_KEY'] = 'test-key'
os.environ['LANGCHAIN_TRACING_V2'] = 'false'
os.environ['REDIS_HOST'] = 'localhost'

# NOW import app (config validates on import)
from app.config import settings
from app.orchestration.state_manager import StateManager

@pytest.fixture
async def mock_redis_client():
    """Mock Redis client"""
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    return client

@pytest.fixture
async def state_manager(mock_redis_client):
    """Create state manager with mock Redis"""
    return StateManager(redis_client=mock_redis_client)

@pytest.fixture
def sample_migration_state():
    """Factory for test state"""
    return {
        'project_id': 'test-proj-123',
        'state_version': 1,
        'phase': WorkflowPhase.INIT,
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        # ... other fields
    }
```

### Testing State Transactions

```python
@pytest.mark.asyncio
async def test_optimistic_locking(state_manager, sample_migration_state):
    """Test optimistic locking conflict detection"""
    
    # Initialize state
    await state_manager.initialize_state('proj-1')
    
    # Simulate two agents reading version 1
    state1 = await state_manager.get_state('proj-1')
    state2 = await state_manager.get_state('proj-1')
    
    assert state1['state_version'] == 1
    assert state2['state_version'] == 1
    
    # Agent 1 commits first
    await state_manager.commit_state(
        'proj-1',
        {'phase': WorkflowPhase.EXTRACTION},
        'agent-1',
        'Phase transition'
    )
    
    # Agent 2's commit should fail (version mismatch)
    with pytest.raises(StateTransactionError):
        await state_manager.commit_state(
            'proj-1',
            {'extracted_facts': {...}},
            'agent-2',
            'Extract facts'
        )
```

### Testing Provider Fallback

```python
@pytest.mark.asyncio
async def test_provider_fallback(monkeypatch):
    """Test automatic fallback to secondary provider"""
    
    # Mock primary provider fails
    primary = AsyncMock(spec=LLMProvider)
    primary.health_check = AsyncMock(return_value=False)
    
    # Mock fallback provider succeeds
    fallback = AsyncMock(spec=LLMProvider)
    fallback.health_check = AsyncMock(return_value=True)
    fallback.generate = AsyncMock(return_value=ProviderResponse(...))
    
    factory = ProviderFactory()
    factory.primary_provider = primary
    factory.fallback_provider = fallback
    factory.primary_status = ProviderStatus.UNAVAILABLE
    factory.fallback_status = ProviderStatus.HEALTHY
    
    # get_provider should return fallback
    provider = await factory.get_provider(prefer_primary=True)
    assert provider == fallback
```

---

## SOLID Principles in Practice {#solid}

### Single Responsibility Principle (SRP)

Each class has ONE reason to change:

```python
# ✓ Good: StateManager only manages state
class StateManager:
    async def commit_state(self, project_id, patch):
        pass

# ✗ Bad: StateManager does HTTP, caching, validation
class StateManager:
    def http_request(self, url):  # Wrong responsibility!
        pass
```

### Open/Closed Principle (OCP)

Open for extension, closed for modification:

```python
# ✓ Good: New provider just implements interface
class AnthropicProvider(LLMProvider):
    async def generate(self, prompt):
        pass

# ✗ Bad: Adding provider requires modifying ProviderFactory
class ProviderFactory:
    if provider_name == "openai":
        ...
    elif provider_name == "gemini":
        ...
    elif provider_name == "anthropic":  # Had to modify!
        ...
```

### Liskov Substitution Principle (LSP)

Subclasses must be substitutable:

```python
# ✓ All providers implement same contract
class ExtractionAgent:
    async def execute(self, state):
        provider = await get_provider()  # Could be any LLMProvider
        facts = await provider.generate_structured(prompt, schema)
        return facts
```

### Interface Segregation Principle (ISP)

Don't force clients to depend on methods they don't use:

```python
# ✓ Agents only need what they use
@abstractmethod
async def generate_structured(self, prompt, schema) -> Dict:
    pass

# ✗ Bad: Single monolithic interface
@abstractmethod
async def do_everything(self, ...):
    pass
```

### Dependency Inversion Principle (DIP)

Depend on abstractions, not concrete implementations:

```python
# ✓ Depends on abstract LLMProvider
class ExtractionAgent:
    def __init__(self, llm: LLMProvider):
        self.llm = llm

# ✗ Depends on concrete OpenAIProvider
class ExtractionAgent:
    def __init__(self):
        self.llm = OpenAIProvider()
```

---

## Performance & Scaling Considerations {#performance}

### Redis Caching

- Store full state in Redis with TTL
- No database queries during workflow execution
- Checkpoint strategy: save full state every N commits

```python
async def commit_state(self, project_id, patch, ...):
    # Update state
    updated = {...}
    
    # Write to Redis
    await self.redis.set(
        f"state:{project_id}",
        updated.model_dump_json(),
        ex=3600  # 1 hour TTL
    )
    
    # Create checkpoint every 5 commits
    if self._checkpoints_count % 5 == 0:
        await self._create_checkpoint(project_id, updated)
```

### Concurrent Agent Execution

- Agents read state in parallel (all get same version)
- Only one agent updates at a time (lock at commit)
- LangGraph serializes execution through supervisor

```
Time ─────────────────────>
Agent A: [read v5] [process] [commit v6] ───
Agent B:                      [read v6] [process] [commit v7]
Agent C:                                       [read v7] [process] [commit v8]
```

### Streaming vs Polling

- SSE (Server-Sent Events): Push from server
- Polling: Pull from client every N seconds
- Use SSE for real-time, polling as fallback

```
SSE (Real-time):
┌─────────────────────────────────────────┐
│ Client opens EventSource                │
└─────────────────────────────────────────┘
           │
      [Server sends state_update]
           │
      [Client processes]
           │
      [Server sends phase_transition]
           │
      [Client processes]

Polling (Fallback):
every 2s: GET /api/orchestration/state/{projectId}
```

---

## Interview Q&A {#interview-qa}

### Q1: How would you design a workflow orchestration system for AI agents?

**A:** I'd use three layers:

1. **State Layer:** Immutable, versioned TypedDict with Annotated reducers for safe concurrent updates
2. **Orchestration Layer:** LangGraph with supervisor routing and conditional edges
3. **API Layer:** FastAPI with SSE for real-time updates

Key decisions:
- Optimistic locking (version checking) instead of pessimistic locks for scalability
- Provider pattern with circuit breaker for resilience
- Annotated list/dict merging to handle concurrent agent updates safely

### Q2: What happens if two agents try to update state simultaneously?

**A:** 
- Both read state version 5
- Agent A processes and commits first → state version becomes 6
- Agent B tries to commit with data from version 5
- Version check fails: expected 5, got 6 → `StateTransactionError`
- Agent B retries, reading version 6, and commits as version 7

This is optimistic locking—we detect conflicts instead of preventing them.

### Q3: How do you handle provider failures (e.g., OpenAI API down)?

**A:** Circuit breaker pattern:
- Primary provider starts HEALTHY
- Failure → increment failure_count
- After 3 failures → mark UNAVAILABLE
- get_provider() tries primary (HEALTHY) first
- If not available, falls back to secondary (Gemini)
- Next successful call resets failure_count

This allows graceful degradation and automatic recovery.

### Q4: Why use FastAPI async instead of regular Python?

**A:** 
- I/O operations (HTTP, Redis, LLM calls) are async and can't block
- With sync code, each request blocks a thread (128 threads max)
- With async, one thread serves 1000+ concurrent requests via event loop
- Allows efficient concurrent agent execution and real-time SSE streaming

### Q5: How would you test this without external APIs?

**A:**
- Mock LLM providers with AsyncMock
- Mock Redis with AsyncMock
- Use test environment variables (set before app import)
- Create test fixtures for state, agents, providers
- Use pytest markers for unit vs integration tests

### Q6: What's the difference between SSE and WebSocket?

**A:**
- **SSE:** One-way (server → client), simpler, auto-reconnect, HTTP standard
- **WebSocket:** Two-way, more overhead, bidirectional communication
- For this use case (server pushing updates), SSE is better—simpler and sufficient

---

## Key Takeaways

1. **Immutable state with versioning** is safer than mutable shared state
2. **Provider pattern + circuit breaker** handles failures gracefully
3. **Optimistic locking** enables concurrent reads with safe writes
4. **FastAPI async** enables high concurrency efficiently
5. **SOLID principles** make code maintainable and testable
6. **Error handling hierarchy** with specific exceptions enables recovery strategies

---

## References

- **LangGraph:** State graphs for multi-agent systems
- **Pydantic:** Type validation and serialization
- **FastAPI:** Modern async web framework
- **tenacity:** Retry patterns with exponential backoff
- **Redis:** In-memory data store for fast state access

---

**Made with Bob**
