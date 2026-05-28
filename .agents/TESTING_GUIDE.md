# Testing Guide & Verification Procedures

**Purpose**: Comprehensive testing procedures for the Migration Copilot POC.  
**Last Updated**: 2026-05-28  
**Applies To**: All AI agents working on this project  

---

## 🎯 Testing Philosophy

**For POC Development**:
- ✅ Manual testing is acceptable
- ✅ Focus on critical paths
- ✅ Verify each phase before moving to next
- ✅ Document test results
- ❌ Don't over-engineer test infrastructure for POC

**For Production**:
- Unit tests for all agents
- Integration tests for workflows
- E2E tests for critical flows
- Load testing
- Security testing

---

## 🧪 Testing Checklist

### Phase 1: Infrastructure Setup

**Backend Startup**:
```bash
# Terminal 1: Start backend
cd backend
python -m uvicorn app.main:app --reload --port 8000

# Expected output:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# INFO:     Application startup complete
```

**Verification**:
- [ ] Backend starts without errors
- [ ] Health check responds: `curl http://localhost:8000/health`
- [ ] API docs accessible: http://localhost:8000/docs
- [ ] No import errors in logs

**Frontend Startup**:
```bash
# Terminal 2: Start frontend
cd frontend
npm start

# Expected output:
# Compiled successfully!
# webpack compiled with 0 warnings
# Local: http://localhost:3000
```

**Verification**:
- [ ] Frontend starts without errors
- [ ] No console errors in browser
- [ ] IBM Carbon styles load correctly
- [ ] Navigation works

---

### Phase 2: MCP Integration

**Test MCP Connection**:
```bash
# Test MCP health
curl http://localhost:8000/api/mcp/health

# Expected response:
{
  "status": "healthy",
  "mcp_configured": true,
  "base_url": "http://localhost:3100"
}
```

**Test Context Retrieval**:
```bash
# Test context retrieval
curl -X POST http://localhost:8000/api/mcp/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "profile": "context_retrieval_profile",
    "filters": {}
  }'

# Expected response:
{
  "sources": [...],
  "total_documents": 5,
  "retrieved_at": "2026-05-28T..."
}
```

**Verification**:
- [ ] MCP connector initializes
- [ ] Bearer token is set
- [ ] Context retrieval returns data
- [ ] No authentication errors
- [ ] Response is valid JSON

---

### Phase 3: Document Upload

**Test Document Upload**:
1. Navigate to http://localhost:3000/upload
2. Select a project (or create new)
3. Upload test documents:
   - PDF: Technical architecture doc
   - DOCX: Requirements document
   - XLSX: Dependency matrix

**Verification**:
- [ ] File upload succeeds
- [ ] Progress indicator shows
- [ ] Success notification appears
- [ ] Document count updates
- [ ] No console errors

**Backend Verification**:
```bash
# Check uploaded documents
curl http://localhost:8000/api/projects/{project_id}/documents

# Expected response:
{
  "documents": [
    {
      "id": "doc-123",
      "filename": "architecture.pdf",
      "content_type": "application/pdf",
      "size": 1024000,
      "uploaded_at": "2026-05-28T..."
    }
  ],
  "total": 1
}
```

**Verification**:
- [ ] Documents stored in Qdrant
- [ ] Embeddings generated
- [ ] Metadata preserved
- [ ] Project association correct

---

### Phase 4: Workflow Execution

**Test Workflow Start**:
1. Navigate to http://localhost:3000/workflow
2. Select project with uploaded documents
3. Click "Execute Workflow"

**Expected Behavior**:
```
Phase 1: INIT
  ↓
Phase 2: CONTEXT_RETRIEVAL
  - Fetching from MCP...
  - Fetching from Qdrant...
  - Normalizing documents...
  ↓
Phase 3: EXTRACTION
  - Extracting technical stack...
  - Extracting dependencies...
  - Assigning confidence scores...
  ↓
Phase 4: QUESTIONNAIRE
  - Identifying gaps...
  - Generating questions...
  ↓
Phase 5: HUMAN_REVIEW
  - Workflow paused
  - Awaiting approval
```

**Verification**:
- [ ] Workflow starts without errors
- [ ] Phase transitions are visible
- [ ] Progress updates in real-time (SSE)
- [ ] Workflow pauses at HUMAN_REVIEW
- [ ] No recursion errors
- [ ] No JSON serialization errors

**Backend Logs Verification**:
```bash
# Check backend logs for:
✅ [context_retrieval_node] Starting context retrieval
✅ [context_retrieval_agent] Retrieved 10 documents
✅ [extraction_node] Starting fact extraction
✅ [extraction_agent] Extracted 25 facts (avg confidence: 0.85)
✅ [questionnaire_node] Generated 8 questions
✅ [human_review_node] Pausing for human review

❌ Redis SET error (datetime serialization)
❌ RecursionError (infinite loop)
❌ KeyError (missing state field)
```

---

### Phase 5: SSE Real-Time Updates

**Test SSE Connection**:
1. Open browser DevTools → Network tab
2. Filter by "stream"
3. Start workflow execution
4. Observe SSE events

**Expected SSE Events**:
```
event: state_update
data: {"project_id": "...", "phase": "context_retrieval", ...}

event: phase_transition
data: {"from": "init", "to": "context_retrieval", ...}

event: state_update
data: {"project_id": "...", "phase": "extraction", ...}

event: phase_transition
data: {"from": "context_retrieval", "to": "extraction", ...}
```

**Verification**:
- [ ] SSE connection established
- [ ] Events received in real-time
- [ ] No connection drops
- [ ] Phase transitions detected
- [ ] State updates are complete (not partial)

**Frontend Console Verification**:
```javascript
// Should see:
✅ SSE connected for project: test-project
✅ Phase transition: init → context_retrieval
✅ State updated: version 1 → 2
✅ Phase transition: context_retrieval → extraction

❌ SSE connection failed
❌ JSON parse error
❌ Missing state fields
```

---

### Phase 6: State Persistence

**Test State Persistence**:
1. Start workflow
2. Wait for HUMAN_REVIEW phase
3. Refresh browser
4. Check if state is preserved

**Verification**:
- [ ] State persists in Redis
- [ ] UI shows correct phase after refresh
- [ ] Extracted facts are visible
- [ ] Questions are displayed
- [ ] No data loss

**Redis Verification**:
```bash
# Check Redis state
redis-cli GET "state:test-project"

# Expected: Valid JSON with all fields
{
  "project_id": "test-project",
  "state_version": 5,
  "phase": "human_review",
  "context_pack": {...},
  "extracted_facts": {...},
  "gap_analysis": {...},
  ...
}
```

---

### Phase 7: Human Review & Approval

**Test Human Review**:
1. Workflow paused at HUMAN_REVIEW
2. Review intake draft
3. Review extracted facts
4. Review questions
5. Click "Approve" (when implemented)

**Expected Behavior**:
```
Before Approval:
- phase: "human_review"
- human_reviewed: false
- Workflow paused

After Approval:
- phase: "migration_planning"
- human_reviewed: true
- approved_by: "user@example.com"
- approved_at: "2026-05-28T..."
- Workflow resumes
```

**Verification**:
- [ ] Intake draft is readable
- [ ] Facts are displayed with confidence scores
- [ ] Questions are prioritized
- [ ] Approval updates state
- [ ] Workflow resumes after approval

---

### Phase 8: Error Handling

**Test Error Scenarios**:

**1. Invalid Project ID**:
```bash
curl http://localhost:8000/api/projects/invalid-id/workflow/execute

# Expected: 404 Not Found
{
  "detail": "Project not found: invalid-id"
}
```

**2. Missing MCP Configuration**:
```bash
# Remove MCP_BEARER_TOKEN from .env
# Restart backend
# Try workflow execution

# Expected: Clear error message
{
  "detail": "MCP not configured: missing bearer token"
}
```

**3. LLM Provider Error**:
```bash
# Set invalid OpenAI API key
# Try workflow execution

# Expected: Graceful error handling
{
  "phase": "error",
  "last_error": "OpenAI API error: Invalid API key",
  "retry_count": 1
}
```

**4. JSON Parsing Error**:
```bash
# Gemini returns markdown-wrapped JSON
# Agent should strip markdown blocks

# Expected: Successful parsing
✅ [extraction_agent] Stripped markdown code blocks
✅ [extraction_agent] Parsed JSON successfully
```

**Verification**:
- [ ] Errors are logged clearly
- [ ] User sees helpful error messages
- [ ] Workflow doesn't crash
- [ ] State is preserved on error
- [ ] Retry logic works

---

## 🔍 Debugging Procedures

### Debug Workflow Stuck

**Symptoms**:
- Workflow doesn't progress
- Phase doesn't change
- No errors in logs

**Debug Steps**:
1. Check current state:
```bash
curl http://localhost:8000/api/projects/{project_id}/workflow/state
```

2. Check Redis state:
```bash
redis-cli GET "state:{project_id}"
```

3. Check LangGraph checkpoints:
```python
# In backend logs, look for:
[workflow] Current phase: extraction
[workflow] State version: 3
[supervisor] Decision: next_node=questionnaire
```

4. Check for infinite loops:
```bash
# Look for repeated log entries:
[human_review_node] Pausing for human review
[supervisor] Decision: next_node=human_review
[human_review_node] Pausing for human review  # ❌ Loop!
```

**Common Causes**:
- Missing `human_reviewed=False` flag
- Supervisor decision logic error
- State version mismatch
- Missing state field

---

### Debug SSE Not Working

**Symptoms**:
- No real-time updates
- UI doesn't refresh
- SSE connection fails

**Debug Steps**:
1. Check SSE connection in DevTools:
```
Network → stream → Status: 200 (should stay open)
```

2. Check backend SSE endpoint:
```bash
curl -N http://localhost:8000/api/projects/{project_id}/workflow/stream

# Should stream events continuously
```

3. Check Redis state sync:
```python
# In backend logs:
[workflow] Syncing state to Redis: version 3
[sse] Polling state from Redis: version 3
[sse] Sending state_update event
```

**Common Causes**:
- Redis not running
- State not syncing to Redis
- SSE endpoint not polling
- Frontend not handling events

---

### Debug JSON Serialization Error

**Symptoms**:
```
Redis SET error: Object of type datetime is not JSON serializable
```

**Debug Steps**:
1. Find the datetime object:
```python
# Search for datetime.utcnow() without .isoformat()
grep -r "datetime.utcnow()" backend/app/
```

2. Check state fields:
```python
# All datetime fields should be strings:
"created_at": "2026-05-28T12:00:00.000Z"  # ✅ String
"created_at": datetime.utcnow()           # ❌ Object
```

3. Add DateTimeEncoder safety net:
```python
# In redis_client.py
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)
```

**Common Causes**:
- Forgot `.isoformat()` on datetime
- ContextPack using datetime objects
- State field not converted to string

---

## 📊 Performance Testing

### Test Workflow Performance

**Metrics to Track**:
- Context retrieval time
- Extraction time
- Question generation time
- Total workflow time
- SSE latency

**Benchmark**:
```bash
# Start workflow and measure time
time curl -X POST http://localhost:8000/api/projects/{project_id}/workflow/execute

# Expected times (POC):
- Context retrieval: 2-5 seconds
- Extraction: 5-10 seconds
- Questionnaire: 3-5 seconds
- Total: 10-20 seconds
```

**Verification**:
- [ ] Workflow completes in reasonable time
- [ ] No timeouts
- [ ] SSE updates are responsive (<1s latency)
- [ ] UI remains responsive

---

## 🎨 UI/UX Testing

### Test UI Components

**Project Selector**:
- [ ] Projects load correctly
- [ ] Create new project works
- [ ] Project selection persists
- [ ] Document count displays

**Document Upload**:
- [ ] File picker works
- [ ] Multiple files can be uploaded
- [ ] Progress indicator shows
- [ ] Success/error notifications appear
- [ ] Supported formats: PDF, DOCX, XLSX

**Workflow Execution**:
- [ ] Execute button works
- [ ] Progress panel shows phases
- [ ] Real-time updates work
- [ ] Phase details are visible
- [ ] Questions are readable (high contrast)

**Visual Verification**:
- [ ] IBM Carbon styling applied
- [ ] Colors are professional (#161616 text, #ffffff bg)
- [ ] No white text on white background
- [ ] Buttons have correct states (disabled, loading)
- [ ] Icons render correctly

---

## 🔐 Security Testing (Basic)

**For POC**:
- [ ] API keys not exposed in frontend
- [ ] Bearer tokens in environment variables
- [ ] No sensitive data in logs
- [ ] CORS configured correctly

**For Production** (future):
- Authentication & authorization
- Input validation & sanitization
- Rate limiting
- SQL injection prevention
- XSS prevention

---

## 📝 Test Documentation

### Document Test Results

**Format**:
```markdown
## Test Session: 2026-05-28

### Environment
- Backend: Running on port 8000
- Frontend: Running on port 3000
- Redis: Running on port 6379
- Qdrant: Running on port 6333

### Test Results

#### Phase 1: Infrastructure ✅
- Backend startup: PASS
- Frontend startup: PASS
- Health checks: PASS

#### Phase 2: MCP Integration ✅
- MCP connection: PASS
- Context retrieval: PASS
- Response format: PASS

#### Phase 3: Document Upload ✅
- PDF upload: PASS
- DOCX upload: PASS
- Embedding generation: PASS

#### Phase 4: Workflow Execution ✅
- Workflow start: PASS
- Phase transitions: PASS
- Pause at human review: PASS

#### Phase 5: SSE Streaming ✅
- SSE connection: PASS
- Real-time updates: PASS
- Phase transitions: PASS

### Issues Found
1. ❌ Questionnaire text unreadable (white on white)
   - Fixed: Added explicit colors
   - Status: RESOLVED

2. ❌ Redis serialization error (datetime)
   - Fixed: Changed to .isoformat()
   - Status: RESOLVED

### Next Steps
- [ ] Test human review approval
- [ ] Test migration planning phase
- [ ] End-to-end demo
```

---

## 🚀 Pre-Demo Checklist

**Before Demo**:
- [ ] All services running
- [ ] Test project created with sample data
- [ ] Workflow executes successfully
- [ ] SSE real-time updates working
- [ ] UI is polished and professional
- [ ] No console errors
- [ ] No backend errors
- [ ] LangSmith traces visible
- [ ] Demo script prepared

**Demo Flow**:
1. Show project selector
2. Upload sample documents
3. Start workflow execution
4. Show real-time progress
5. Show extracted facts
6. Show generated questions
7. Show intake draft (when ready)
8. Show LangSmith traces
9. Explain architecture

---

## 📚 Testing Resources

**Tools**:
- curl: API testing
- Postman: API testing (optional)
- Browser DevTools: Frontend debugging
- Redis CLI: State inspection
- LangSmith: Trace inspection

**Documentation**:
- API Docs: http://localhost:8000/docs
- LangSmith: https://smith.langchain.com/
- IBM Carbon: https://carbondesignsystem.com/

---

**Last Updated**: 2026-05-28  
**Maintained By**: AI Agents Team  
**Status**: Active - Use for all testing