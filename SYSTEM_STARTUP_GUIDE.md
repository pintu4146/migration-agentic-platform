# Migration Copilot - Complete System Startup Guide

This guide will help you start the entire Migration Copilot system from scratch.

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] **Podman installed** (check with `podman --version`)
- [ ] **Python 3.11+** installed (check with `python --version`)
- [ ] **Node.js 18+** installed (check with `node --version`)
- [ ] **Gemini API key** added to `backend/.env`
- [ ] **OpenAI API key** (optional, for primary provider)
- [ ] **LangSmith API key** (optional, for tracing)

---

## Step 1: Setup Podman Machine (Windows Only)

Podman on Windows requires a Linux VM to run containers.

### Run the setup script:

```powershell
cd backend
.\setup-podman.ps1
```

**What this does:**
- Checks if Podman is installed
- Initializes Podman machine if it doesn't exist
- Starts the Podman machine
- Verifies the connection

**Expected output:**
```
✓ Podman is installed: podman version 4.x.x
✓ Podman machine initialized
✓ Podman machine started successfully
✓ Podman is working correctly
```

**If you see errors:**
- Make sure Podman is installed: `winget install RedHat.Podman`
- Restart your terminal after installation
- Run the script again

---

## Step 2: Start Backend Containers

Once Podman is running, start Redis and Qdrant containers.

### Run the container startup script:

```powershell
# Still in backend directory
.\start-containers-simple.ps1
```

**What this does:**
- Creates network `mig26-network`
- Starts Redis container on port 6379
- Starts Qdrant container on ports 6333 (API) and 6334 (gRPC)
- Tests connectivity

**Expected output:**
```
✓ Network mig26-network created
✓ Redis container started
✓ Qdrant container started
✓ Redis is responding
✓ Qdrant is responding
```

**Verify containers are running:**
```powershell
podman ps
```

You should see:
```
CONTAINER ID  IMAGE                       COMMAND     STATUS      PORTS                   NAMES
xxxxx         redis:7-alpine              redis-...   Up 1 min    0.0.0.0:6379->6379/tcp  mig26-redis
xxxxx         qdrant/qdrant:latest        ./entryp... Up 1 min    0.0.0.0:6333->6333/tcp  mig26-qdrant
```

**If containers don't start:**
- Check Podman machine is running: `podman machine list`
- Check logs: `podman logs mig26-redis` or `podman logs mig26-qdrant`
- Try stopping and restarting: `podman stop mig26-redis mig26-qdrant` then run script again

---

## Step 3: Install Backend Dependencies

Install Python packages required by the backend.

### Install dependencies:

```powershell
# Still in backend directory
pip install -r requirements.txt
```

**What this installs:**
- FastAPI (web framework)
- LangGraph (workflow orchestration)
- OpenAI SDK (LLM provider)
- Google GenAI SDK (Gemini provider)
- Redis client (state management)
- Qdrant client (vector store)
- Document parsers (PyMuPDF, python-docx, pandas, openpyxl)
- LangSmith (tracing)

**Expected output:**
```
Successfully installed fastapi-0.109.0 langgraph-0.0.20 openai-1.10.0 ...
```

**If installation fails:**
- Make sure Python 3.11+ is installed
- Try upgrading pip: `python -m pip install --upgrade pip`
- Check for specific error messages

---

## Step 4: Verify Backend Configuration

Make sure your `.env` file has all required settings.

### Check your `.env` file:

```powershell
# View the file
cat backend\.env
```

**Required settings:**

```env
# Primary Provider (OpenAI) - OPTIONAL
PRIMARY_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...your-key-here...

# Fallback Provider (Gemini) - REQUIRED
FALLBACK_PROVIDER=gemini
GEMINI_API_KEY=AIzaSyD...your-key-here...
GEMINI_MODEL=gemini-1.5-pro
GEMINI_TEMPERATURE=0.7
GEMINI_MAX_TOKENS=2000
GEMINI_TIMEOUT=60

# MCP Gateway - OPTIONAL for now
MCP_GATEWAY_URL=http://localhost:8080
MCP_BEARER_TOKEN=your-token-here

# LangSmith - OPTIONAL
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__...your-key-here...
LANGCHAIN_PROJECT=migration-copilot-poc

# Storage - REQUIRED (should match container ports)
REDIS_HOST=localhost
REDIS_PORT=6379
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

**Minimum required for testing:**
- `GEMINI_API_KEY` - Get from https://aistudio.google.com/app/apikey
- `REDIS_HOST=localhost` and `REDIS_PORT=6379`
- `QDRANT_HOST=localhost` and `QDRANT_PORT=6333`

---

## Step 5: Start Backend API Server

Start the FastAPI backend server.

### Run the server:

```powershell
# Still in backend directory
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**What this does:**
- Starts FastAPI server on port 8000
- Enables auto-reload on code changes
- Exposes API endpoints

**Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [xxxxx] using WatchFiles
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**Verify the API is running:**

Open browser to: http://localhost:8000/docs

You should see the **FastAPI Swagger UI** with all API endpoints.

**If server doesn't start:**
- Check if port 8000 is already in use
- Check Redis and Qdrant are running: `podman ps`
- Check logs for specific errors
- Verify `.env` file exists and has correct settings

---

## Step 6: Install Frontend Dependencies

Install Node.js packages for the React frontend.

### Open a NEW terminal and run:

```powershell
cd frontend
npm install
```

**What this installs:**
- React 18.2 (UI framework)
- IBM Carbon Design System (UI components)
- React Router (navigation)
- Axios (HTTP client)
- Vite (build tool)

**Expected output:**
```
added 500+ packages in 30s
```

**If installation fails:**
- Make sure Node.js 18+ is installed: `node --version`
- Try clearing npm cache: `npm cache clean --force`
- Delete `node_modules` and `package-lock.json` if they exist, then try again

---

## Step 7: Start Frontend Dev Server

Start the React development server.

### Run the dev server:

```powershell
# Still in frontend directory
npm run dev
```

**What this does:**
- Starts Vite dev server on port 3000
- Enables hot module replacement (HMR)
- Proxies API calls to backend (port 8000)

**Expected output:**
```
  VITE v5.0.8  ready in 500 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
  ➜  press h to show help
```

**Open the application:**

Navigate to: http://localhost:3000

You should see the **Migration Copilot Dashboard**.

**If frontend doesn't start:**
- Check if port 3000 is already in use
- Make sure backend is running on port 8000
- Check browser console for errors

---

## Step 8: Verify System Health

Check that all components are working together.

### System Health Checklist:

1. **Podman Containers:**
   ```powershell
   podman ps
   ```
   Should show `mig26-redis` and `mig26-qdrant` running

2. **Backend API:**
   - Open: http://localhost:8000/docs
   - Should show Swagger UI with endpoints

3. **Frontend UI:**
   - Open: http://localhost:3000
   - Should show Dashboard with status indicators

4. **Dashboard Status:**
   - Backend API: Should show "Connected" (green)
   - Redis: Should show "Connected" (green)
   - Qdrant: Should show "Connected" (green)
   - MCP Gateway: May show "Not Configured" (yellow) - this is OK for now

---

## Step 9: Test Document Upload

Test the document upload functionality.

### Create test files:

Create a file `test-app.properties` with this content:

```properties
# Application Configuration
app.name=LegacyApp
app.version=2.1.0
server.port=8080
database.url=jdbc:mysql://localhost:3306/appdb
database.username=admin
cache.enabled=true
```

### Upload the file:

1. Navigate to **Upload** page in the UI
2. Enter project ID: `test-project-001`
3. Drag and drop `test-app.properties` or click to browse
4. Click **Upload Documents**
5. Wait for upload to complete

**Expected result:**
- Upload status shows "Success"
- Parser used: "PropertiesParser"
- Chunks created: 1-2 chunks
- Document ID is displayed

---

## Step 10: Test Workflow Execution

Test the complete workflow orchestration.

### Start workflow:

1. Navigate to **Workflow** page
2. Enter project ID: `test-project-001`
3. Enter document IDs from upload (comma-separated)
4. Click **Start Workflow**

**Expected behavior:**
- Progress indicator shows 9 phases
- Current phase updates in real-time
- State viewer shows workflow state
- Phases progress: init → context_retrieval → extraction → questionnaire → ...

**Monitor progress:**
- Watch the phase indicator
- Expand "Current State" to see details
- Check "Phase History" for completed phases

---

## Step 11: View Extracted Facts

Once workflow reaches extraction phase, view the results.

### View facts:

1. Navigate to **Facts** page
2. Enter project ID: `test-project-001`
3. Click **Load Facts**

**Expected result:**
- Tabs show 7 categories:
  - Technical Stack
  - Dependencies
  - Runtime Configuration
  - Deployment Strategy
  - Architecture Decisions
  - Security/Compliance
  - Risks
- Each tab shows extracted facts with confidence scores
- Evidence links show source documents

---

## Troubleshooting Common Issues

### Issue: Podman machine won't start

**Solution:**
```powershell
# Stop and remove existing machine
podman machine stop
podman machine rm

# Reinitialize
podman machine init --cpus 2 --memory 4096 --disk-size 50
podman machine start
```

### Issue: Containers won't start

**Solution:**
```powershell
# Stop all containers
podman stop mig26-redis mig26-qdrant

# Remove containers
podman rm mig26-redis mig26-qdrant

# Remove volumes (WARNING: deletes data)
podman volume rm mig26-redis-data mig26-qdrant-data

# Run startup script again
.\start-containers-simple.ps1
```

### Issue: Backend API errors

**Solution:**
1. Check `.env` file has correct settings
2. Verify Gemini API key is valid
3. Check Redis and Qdrant are running: `podman ps`
4. Check backend logs for specific errors
5. Restart backend server

### Issue: Frontend can't connect to backend

**Solution:**
1. Verify backend is running on port 8000
2. Check browser console for CORS errors
3. Verify `vite.config.js` has correct proxy settings
4. Restart frontend dev server

### Issue: Workflow gets stuck

**Solution:**
1. Check backend logs for errors
2. Verify LLM provider (Gemini) is responding
3. Check Redis connection
4. Check Qdrant connection
5. Try with a smaller test document

---

## Quick Reference Commands

### Start Everything:

```powershell
# Terminal 1: Start containers
cd backend
.\setup-podman.ps1
.\start-containers-simple.ps1

# Terminal 2: Start backend
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3: Start frontend
cd frontend
npm run dev
```

### Stop Everything:

```powershell
# Stop frontend: Press Ctrl+C in Terminal 3

# Stop backend: Press Ctrl+C in Terminal 2

# Stop containers:
cd backend
podman stop mig26-redis mig26-qdrant
```

### Check Status:

```powershell
# Podman machine
podman machine list

# Containers
podman ps

# Container logs
podman logs mig26-redis
podman logs mig26-qdrant

# Backend API
curl http://localhost:8000/health

# Frontend
curl http://localhost:3000
```

---

## System Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                     User Browser                             │
│                  http://localhost:3000                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  React Frontend (Vite)                       │
│              IBM Carbon Design System                        │
│                    Port: 3000                                │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/REST
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend                             │
│              LangGraph Orchestration                         │
│                    Port: 8000                                │
└─────┬──────────────────┬──────────────────┬─────────────────┘
      │                  │                  │
      ▼                  ▼                  ▼
┌──────────┐      ┌──────────┐      ┌──────────────┐
│  Redis   │      │  Qdrant  │      │ Gemini API   │
│  :6379   │      │  :6333   │      │ (External)   │
└──────────┘      └──────────┘      └──────────────┘
```

---

## Next Steps After System is Running

1. **Test with real documents:**
   - Upload PDF, DOCX, Excel files
   - Test different document types
   - Verify parsing and extraction

2. **Configure MCP Gateway (optional):**
   - Set up IBM Context Studio
   - Add MCP_GATEWAY_URL and MCP_BEARER_TOKEN to `.env`
   - Test Confluence integration

3. **Enable LangSmith tracing (optional):**
   - Get API key from https://smith.langchain.com
   - Add LANGCHAIN_API_KEY to `.env`
   - View traces in LangSmith dashboard

4. **Proceed to Phase 5:**
   - Implement Intake Draft Agent
   - Implement Review/Validation Agent
   - Add human review UI

---

## Support

If you encounter issues not covered in this guide:

1. Check the logs:
   - Backend: Terminal 2 output
   - Frontend: Browser console (F12)
   - Containers: `podman logs <container-name>`

2. Verify configuration:
   - `.env` file has all required settings
   - API keys are valid
   - Ports are not in use by other applications

3. Review documentation:
   - `README.md` - Project overview
   - `QUICK_START_TESTING.md` - Testing guide
   - `PHASE7_FRONTEND_UI_COMPLETE.md` - Frontend details

---

**System Status:** Ready for testing and development!

**Last Updated:** 2026-05-27