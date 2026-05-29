# SSE Datetime Serialization Fix

## Problem

When implementing SSE real-time updates with LangGraph state synchronization to Redis, we encountered this error:

```
Redis SET error for key 'state:pintu-test': Object of type datetime is not JSON serializable
```

## Root Cause

The workflow state contains `datetime` objects (e.g., `created_at`, `updated_at`, `last_committed_at`) that cannot be directly serialized to JSON by Python's default `json.dumps()` function.

When we tried to sync LangGraph state to Redis after each node completion, the serialization failed because:

```python
# This fails with datetime objects
serialized = json.dumps(state)  # ❌ TypeError: Object of type datetime is not JSON serializable
```

## Solution

Added a custom JSON encoder that converts `datetime` objects to ISO 8601 strings:

### 1. Created DateTimeEncoder Class

**File**: `backend/app/storage/redis_client.py`

```python
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""
    
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)
```

### 2. Updated Redis set() Method

```python
async def set(
    self,
    key: str,
    value: Dict[str, Any],
    ttl: Optional[int] = None
) -> bool:
    """Set value in Redis with optional TTL."""
    try:
        # Use custom encoder to handle datetime objects
        serialized = json.dumps(value, cls=DateTimeEncoder)  # ✅ Works!
        ttl_seconds = ttl or settings.redis_ttl
        
        await self._client.setex(
            key,
            timedelta(seconds=ttl_seconds),
            serialized
        )
        return True
    except Exception as e:
        logger.error(f"Redis SET error for key '{key}': {e}")
        return False
```

## How It Works

1. **Before**: `datetime(2026, 5, 28, 20, 10, 50)` → ❌ JSON serialization error
2. **After**: `datetime(2026, 5, 28, 20, 10, 50)` → ✅ `"2026-05-28T20:10:50"`

The custom encoder:
- Checks if the object is a `datetime` instance
- Converts it to ISO 8601 format string using `.isoformat()`
- Falls back to default behavior for other types

## Benefits

1. **Automatic Conversion**: All datetime objects are automatically converted
2. **ISO 8601 Standard**: Uses industry-standard datetime format
3. **Reversible**: Can be parsed back to datetime using `datetime.fromisoformat()`
4. **No Code Changes Needed**: Works transparently throughout the codebase

## Testing

### Before Fix
```bash
# Terminal output showed:
Redis SET error for key 'state:pintu-test': Object of type datetime is not JSON serializable
```

### After Fix
```bash
# Should see:
Workflow node 'context_retrieval_node' completed, phase: context_retrieval, version: 4
# No Redis errors!
```

## Current Architecture

With this fix, our SSE architecture works as follows:

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Workflow                        │
│                                                              │
│  1. Node completes (e.g., context_retrieval)                │
│     ↓                                                        │
│  2. workflow.astream() yields node output                   │
│     ↓                                                        │
│  3. Merge output with current state                         │
│     ↓                                                        │
│  4. _sync_state_to_redis(project_id, state)                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      Redis Client                            │
│                                                              │
│  5. json.dumps(state, cls=DateTimeEncoder)                  │
│     - Converts datetime → ISO 8601 string                   │
│     ↓                                                        │
│  6. redis.setex(key, ttl, serialized_json)                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      SSE Endpoint                            │
│                                                              │
│  7. Poll Redis every 0.5 seconds                            │
│     ↓                                                        │
│  8. Detect state change (version or phase)                  │
│     ↓                                                        │
│  9. Send SSE event to frontend                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      Frontend                                │
│                                                              │
│  10. EventSource receives event                             │
│     ↓                                                        │
│  11. Update UI with phase transition                        │
└─────────────────────────────────────────────────────────────┘
```

## Alternative Approaches Considered

### Option A: Convert datetime to string before Redis
```python
# Manually convert before saving
state_copy = state.copy()
state_copy['created_at'] = state['created_at'].isoformat()
state_copy['updated_at'] = state['updated_at'].isoformat()
await redis.set(key, state_copy)
```
**Rejected**: Too manual, error-prone, requires changes everywhere

### Option B: Use pickle instead of JSON
```python
import pickle
serialized = pickle.dumps(state)
```
**Rejected**: Not human-readable, security concerns, not web-friendly

### Option C: Custom serialization function
```python
def serialize_state(state):
    # Custom logic for each field
    pass
```
**Rejected**: Too complex, hard to maintain

### Option D: Use Pydantic models
```python
from pydantic import BaseModel

class MigrationState(BaseModel):
    created_at: datetime
    
    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
```
**Considered for future**: Good for type safety, but requires refactoring

## Future Improvements

1. **Add datetime parsing on read**: Automatically convert ISO strings back to datetime
2. **Support more types**: Handle `date`, `time`, `timedelta`, `Decimal`, etc.
3. **Use Pydantic**: Migrate to Pydantic models for better type safety
4. **Add validation**: Ensure datetime strings are valid ISO 8601

## Related Files

- `backend/app/storage/redis_client.py` - Redis client with custom encoder
- `backend/app/orchestration/workflow.py` - Workflow with state syncing
- `backend/app/api/orchestration.py` - SSE endpoint
- `backend/app/orchestration/state.py` - State definitions

## Conclusion

This quick fix resolves the datetime serialization issue while maintaining the current architecture. The solution is:
- ✅ Simple and elegant
- ✅ Automatic and transparent
- ✅ Standards-compliant (ISO 8601)
- ✅ Minimal code changes
- ✅ Production-ready

For future iterations, we can consider migrating to true LangGraph native streaming (Option A from the original discussion) which would eliminate the need for Redis syncing entirely.