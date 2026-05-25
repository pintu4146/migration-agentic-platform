# Test Before Phase 4 - Quick Start Guide

This is a simplified guide to test everything before starting Phase 4: Core Agents.

## Prerequisites Checklist

- [ ] Containers are running (Redis + Qdrant)
- [ ] `.env` file is configured with all API keys
- [ ] Python virtual environment is activated
- [ ] Dependencies are installed

## Quick Test (5 minutes)

### Step 1: Start Containers

```powershell
cd backend
.\start-containers-simple.ps1
```

**Expected output:**
```
✓ Redis container started
✓ Qdrant container started
```

### Step 2: Run Quick Test

```powershell
.\quick_test.ps1
```

**Expected output:**
```
=== Quick System Test ===

1. Testing Redis...
   ✓ Redis OK

2. Testing Qdrant...
   ✓ Qdrant OK (version: 1.x.x)

3. Testing FastAPI...
   ✗ FastAPI not running
   Run: uvicorn app.main:app --reload --port 8000
```

### Step 3: Start FastAPI

```powershell
# In a new terminal
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Step 4: Run Quick Test Again

```powershell
# In another terminal
cd backend
.\quick_test.ps1
```

**Expected output:**
```
=== Quick System Test ===

1. Testing Redis...
   ✓ Redis OK

2. Testing Qdrant...
   ✓ Qdrant OK (version: 1.x.x)

3. Testing FastAPI...
   ✓ FastAPI OK (status: healthy)

4. Checking Redis data...
   ℹ Redis is empty (no workflows created yet)

5. Checking Qdrant collections...
   ℹ Qdrant is empty (no collections yet)

=== Test Complete ===
```

## Test Redis Updates (10 minutes)

### Test 1: Create a Workflow

```powershell
# Create workflow
$body = @{
    project_id = "test_app_001"
    user_id = "test_user"
} | ConvertTo-Json

$workflow = Invoke-RestMethod -Uri "http://localhost:8000/api/orchestration/workflow/create" -Method Post -Body $body -ContentType "application/json"

Write-Host "Workflow created: $($workflow.project_id)"
```

**Expected output:**
```
Workflow created: test_app_001
```

### Test 2: Check Redis

```powershell
# Check if state exists in Redis
podman exec mig26-redis redis-cli EXISTS "state:test_app_001"
```

**Expected output:**
```
(integer) 1
```

This means the state was saved to Redis! ✓

### Test 3: Get State

```powershell
# Get the state from Redis
podman exec mig26-redis redis-cli GET "state:test_app_001"
```

**Expected output:**
```json
{"project_id":"test_app_001","state_version":1,"phase":"context_retrieval",...}
```

### Test 4: Get State via API

```powershell
$state = Invoke-RestMethod -Uri "http://localhost:8000/api/orchestration/workflow/test_app_001/state" -Method Get

Write-Host "Phase: $($state.phase)"
Write-Host "Version: $($state.state_version)"
```

**Expected output:**
```
Phase: context_retrieval
Version: 1
```

### Test 5: List All Workflows

```powershell
$list = Invoke-RestMethod -Uri "http://localhost:8000/api/orchestration/workflow/list" -Method Get

Write-Host "Total workflows: $($list.count)"
$list.workflows | ForEach-Object { Write-Host "  - $($_.project_id)" }
```

**Expected output:**
```
Total workflows: 1
  - test_app_001
```

### Test 6: Monitor Redis in Real-Time

```powershell
# In a separate terminal, monitor Redis
podman exec -it mig26-redis redis-cli MONITOR
```

Now create another workflow and watch Redis commands appear in real-time!

### Test 7: Cleanup

```powershell
# Delete the test workflow
Invoke-RestMethod -Uri "http://localhost:8000/api/orchestration/workflow/test_app_001" -Method Delete

# Verify it's gone from Redis
podman exec mig26-redis redis-cli EXISTS "state:test_app_001"
```

**Expected output:**
```
(integer) 0
```

## Verify State Updates Work

### Test: State Version Increment

```powershell
# Create workflow
$body = @{
    project_id = "version_test"
    user_id = "test_user"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/orchestration/workflow/create" -Method Post -Body $body -ContentType "application/json"

# Check initial version
$state1 = Invoke-RestMethod -Uri "http://localhost:8000/api/orchestration/workflow/version_test/state" -Method Get
Write-Host "Initial version: $($state1.state_version)"

# Update state (this happens internally when workflow runs)
# For now, just verify the version is 1

# Cleanup
Invoke-RestMethod -Uri "http://localhost:8000/api/orchestration/workflow/version_test" -Method Delete
```

## Common Issues and Solutions

### Issue 1: Redis Connection Failed

**Symptom:**
```
✗ Redis FAILED
```

**Solution:**
```powershell
# Check if container is running
podman ps | Select-String "redis"

# If not running, start it
.\start-containers-simple.ps1

# If still failing, check logs
podman logs mig26-redis
```

### Issue 2: Qdrant Connection Failed

**Symptom:**
```
✗ Qdrant FAILED
```

**Solution:**
```powershell
# Check if container is running
podman ps | Select-String "qdrant"

# If not running, start it
.\start-containers-simple.ps1

# If still failing, check logs
podman logs mig26-qdrant
```

### Issue 3: FastAPI Not Starting

**Symptom:**
```
ERROR:    [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000)
```

**Solution:**
```powershell
# Port 8000 is already in use
# Find what's using it
netstat -ano | Select-String ":8000"

# Kill the process or use a different port
uvicorn app.main:app --reload --port 8001
```

### Issue 4: State Not Saving to Redis

**Symptom:**
```
podman exec mig26-redis redis-cli KEYS "*"
(empty array)
```

**Solution:**
```powershell
# Check FastAPI logs for errors
# Check if Redis client is initialized
python -c "from app.storage.redis_client import RedisClient; import asyncio; asyncio.run(RedisClient().ping())"

# Should print: True
```

## Success Criteria

Before moving to Phase 4, verify:

- ✅ `.\quick_test.ps1` shows all green checkmarks
- ✅ Can create workflow via API
- ✅ State appears in Redis (`podman exec mig26-redis redis-cli KEYS "*"`)
- ✅ Can retrieve state via API
- ✅ Can list workflows
- ✅ Can delete workflow
- ✅ State disappears from Redis after deletion

## What Gets Tested

### ✅ Infrastructure
- Redis container running
- Qdrant container running
- FastAPI server running

### ✅ Storage Layer
- Redis connection works
- Can save data to Redis
- Can retrieve data from Redis
- Keys are namespaced correctly

### ✅ State Management
- Can create workflow state
- State is persisted to Redis
- State version tracking works
- Can retrieve state

### ✅ API Layer
- Health endpoint works
- Workflow creation works
- State retrieval works
- Workflow listing works
- Workflow deletion works

## What's NOT Tested Yet

These will be tested in Phase 4:

- ❌ MCP context retrieval (needs real MCP data)
- ❌ LLM provider integration (needs API calls)
- ❌ Agent execution (not implemented yet)
- ❌ Workflow transitions (not implemented yet)
- ❌ LangSmith tracing (needs workflow execution)

## Next Steps

Once all tests pass:

1. **Commit your changes:**
   ```powershell
   git add .
   git commit -m "Phase 3 complete: Testing guide and .gitignore updates"
   git push
   ```

2. **Ready for Phase 4:**
   - Multi-project architecture (parked for later)
   - Core Agents implementation (next!)

## Quick Reference

### Start Everything
```powershell
# Terminal 1: Containers
cd backend
.\start-containers-simple.ps1

# Terminal 2: FastAPI
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# Terminal 3: Tests
cd backend
.\quick_test.ps1
```

### Stop Everything
```powershell
# Stop FastAPI: Ctrl+C in Terminal 2

# Stop containers
cd backend
.\stop-containers.ps1
```

### Reset Everything
```powershell
cd backend
.\reset-all-data.ps1
```

## Detailed Testing

For comprehensive testing, see:
- `TESTING_GUIDE.md` - Full test suite with all scenarios
- `CONTAINER_SETUP.md` - Container configuration details
- `WHICH_SCRIPT_TO_USE.md` - Script selection guide

## Time Estimate

- Quick test: **5 minutes**
- Redis update test: **10 minutes**
- Full test suite: **30 minutes**

Start with the quick test, then do Redis updates test. That's enough to verify everything works before Phase 4!