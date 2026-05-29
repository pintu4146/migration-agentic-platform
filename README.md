# Migration Copilot - Enterprise Application Modernization POC

A proof-of-concept AI-powered copilot for enterprise application modernization, featuring multi-agent orchestration, configurable context retrieval, and transparent execution tracing.

## 🎯 Overview

The Migration Copilot assists with:
- Ingesting Confluence pages and uploaded documents
- Fetching context using configurable MCP connectors
- Extracting migration-relevant facts
- Generating questionnaire gaps
- Drafting intake documents
- Supporting human review workflows
- Generating migration plans with cloud infrastructure recommendations
- Providing transparent traces using LangSmith

## 🏗️ Architecture

### Tech Stack

**Frontend:**
- React
- IBM Carbon Design System

**Backend:**
- FastAPI
- Python 3.11+

**Agent Orchestration:**
- LangGraph (supervisor-led multi-agent workflow)
- Transactional state management with ACID properties

**LLM Providers:**
- OpenAI (primary)
- Google Gemini (fallback)
- Provider abstraction layer with circuit breaker pattern

**Context Sources:**
- MCP connector (Confluence Cloud)
- Document parsing (PDF, DOCX, Excel)

**Storage:**
- Redis (caching)
- Qdrant (vector storage)

**Observability:**
- LangSmith (tracing)
- Prometheus + Grafana (metrics)

**Container Runtime:**
- Podman

## 📁 Project Structure

```
mig-26/
├── docs/                           # Comprehensive documentation
│   ├── 00-architecture-overview.md
│   ├── 01-phase1-foundation.md
│   ├── 02-phase2-mcp-connector.md
│   ├── 03-phase3-orchestration.md
│   ├── 04-phase4-core-agents.md
│   ├── 05-phase5-intake-review.md
│   ├── 06-phase6-migration-planning.md
│   ├── 07-phase7-frontend-ui.md
│   ├── 08-phase8-deployment.md
│   ├── 09-single-point-of-failure-analysis.md
│   ├── 10-agent-orchestration-analysis.md
│   └── 11-observability-stack.md
│
├── backend/                        # FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI application
│   │   ├── config.py              # Configuration management
│   │   ├── logging_config.py      # Structured logging
│   │   ├── models/                # Pydantic schemas
│   │   ├── providers/             # LLM provider abstraction
│   │   │   ├── base.py
│   │   │   ├── openai_provider.py
│   │   │   ├── gemini_provider.py
│   │   │   └── factory.py
│   │   └── tracing/               # LangSmith integration
│   │       └── langsmith.py
│   ├── tests/                     # Test suite
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                       # React frontend (Phase 7)
│
├── podman-compose.yml             # Container orchestration
├── .env.example                   # Environment template
└── README.md
```

## 🚀 Quick Start

### Prerequisites

**System Requirements:**
- Python 3.10 or higher
- Node.js 18+ and npm (for frontend)
- Podman Desktop (recommended) or Docker Desktop
- Git
- Windows PowerShell (for Windows users)

**Required API Keys:**
- OpenAI API key (primary LLM provider)
- Google Gemini API key (fallback LLM provider)

**Optional:**
- LangSmith API key (for tracing and observability)
- Confluence Cloud access (for MCP connector)

### 🎯 Complete Startup Guide (Recommended)

Follow these steps in order for a smooth setup:

#### Step 1: System Prerequisites

**Install Podman Desktop:**
1. Download from: https://podman-desktop.io/downloads
2. Install and launch Podman Desktop
3. Verify installation:
   ```powershell
   podman --version
   podman-compose --version
   ```

**Install Python 3.10+:**
1. Download from: https://www.python.org/downloads/
2. During installation, check "Add Python to PATH"
3. Verify:
   ```powershell
   python --version
   ```

**Install Node.js 18+:**
1. Download from: https://nodejs.org/
2. Install LTS version
3. Verify:
   ```powershell
   node --version
   npm --version
   ```

#### Step 2: Clone and Configure

```powershell
# Clone the repository
git clone <repository-url>
cd mig-26

# Copy environment template
cp backend/.env.example backend/.env

# Edit .env file and add your API keys
notepad backend/.env
```

**Required Environment Variables:**
```bash
# LLM Providers (REQUIRED)
OPENAI_API_KEY=sk-your-openai-key-here
GEMINI_API_KEY=your-gemini-key-here

# Application Settings
ENVIRONMENT=development
LOG_LEVEL=INFO
PRIMARY_PROVIDER=openai
FALLBACK_PROVIDER=gemini

# Optional: LangSmith Tracing
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_PROJECT=migration-copilot-poc

# Optional: MCP Connector (Confluence)
MCP_BASE_URL=https://your-domain.atlassian.net/wiki
MCP_BEARER_TOKEN=your-confluence-token
```

#### Step 3: Backend Setup

**Run the setup script (Windows):**
```powershell
cd backend
.\setup-podman.ps1
```

This script will:
- Create Python virtual environment
- Install all dependencies
- Verify imports
- Set up Podman containers (Redis, Qdrant)

**Or manually:**
```powershell
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "import fastapi; import langchain; print('✓ All imports successful')"
```

#### Step 4: Start Infrastructure Containers

**Start Redis and Qdrant:**
```powershell
cd backend
.\start-containers-simple.ps1
```

This will start:
- **Redis** on `localhost:6379` (state management)
- **Qdrant** on `localhost:6333` (vector storage)

**Verify containers are running:**
```powershell
podman ps
```

You should see:
```
CONTAINER ID  IMAGE                              STATUS      PORTS
xxxxx         docker.io/library/redis:7-alpine   Up          0.0.0.0:6379->6379/tcp
xxxxx         docker.io/qdrant/qdrant:latest     Up          0.0.0.0:6333->6333/tcp
```

#### Step 5: Start Backend Server

```powershell
cd backend

# Activate virtual environment (if not already activated)
.\venv\Scripts\activate

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output:**
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Verify backend is running:**
- API Health: http://localhost:8000/health
- API Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

#### Step 6: Start Frontend

**Open a new terminal:**
```powershell
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

**Expected output:**
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

**Access the application:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000

#### Step 7: Verify Complete Setup

**Test the full stack:**

1. **Check Backend Health:**
   ```powershell
   curl http://localhost:8000/health
   ```
   Expected: `{"status":"healthy"}`

2. **Check Provider Health:**
   ```powershell
   curl http://localhost:8000/health/providers
   ```
   Expected: Provider status with OpenAI/Gemini health

3. **Check Frontend:**
   - Open http://localhost:5173
   - You should see the Migration Copilot dashboard

4. **Check Containers:**
   ```powershell
   podman ps
   ```
   Expected: Redis and Qdrant running

### 🔄 Daily Development Workflow

**Start everything:**
```powershell
# Terminal 1: Start containers
cd backend
.\start-containers-simple.ps1

# Terminal 2: Start backend
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3: Start frontend
cd frontend
npm run dev
```

**Stop everything:**
```powershell
# Stop backend: Ctrl+C in backend terminal
# Stop frontend: Ctrl+C in frontend terminal

# Stop containers
cd backend
.\stop-containers.ps1
```

### 🐛 Troubleshooting

**Backend won't start:**
- Check if virtual environment is activated
- Verify all dependencies: `pip list`
- Check .env file has required API keys
- Check port 8000 is not in use: `netstat -ano | findstr :8000`

**Containers won't start:**
- Verify Podman Desktop is running
- Check if ports are available: `netstat -ano | findstr :6379` and `netstat -ano | findstr :6333`
- Try: `podman system prune -a` (removes all containers and images)

**Frontend won't start:**
- Check Node.js version: `node --version` (should be 18+)
- Delete node_modules and reinstall: `rm -rf node_modules && npm install`
- Check port 5173 is not in use

**API calls failing:**
- Verify backend is running: http://localhost:8000/health
- Check browser console for CORS errors
- Verify .env has correct API keys

### Option 1: Quick Start (Windows)

**First Time Setup:**
```cmd
# Run setup script (one-time)
dev-setup.cmd

# Edit backend\.env and add your API keys
notepad backend\.env
```

**Start Development Server:**
```cmd
# Run this every time you want to start the server
dev-run.cmd
```

The server will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Option 2: Manual Setup (All Platforms)

**1. Clone and Setup**
```bash
# Clone repository
git clone <repository-url>
cd mig-26

# Copy environment template
cp backend/.env.example backend/.env

# Edit .env with your API keys
```

**2. Backend Setup**
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run import test
python test_imports.py

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Container Setup (Podman)

```bash
# Build and start all services
podman-compose up -d

# View logs
podman-compose logs -f backend

# Stop services
podman-compose down
```

### 4. Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Check provider health
curl http://localhost:8000/health/providers

# View API documentation
open http://localhost:8000/docs
```

## 🔧 Configuration

### Environment Variables

Key configuration options (see `.env.example` for full list):

```bash
# Application
ENVIRONMENT=development
LOG_LEVEL=INFO

# LLM Providers
PRIMARY_PROVIDER=openai
FALLBACK_PROVIDER=gemini
OPENAI_API_KEY=your-key
GEMINI_API_KEY=your-key

# LangSmith Tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-key
LANGCHAIN_PROJECT=migration-copilot-poc

# MCP Connector
MCP_BASE_URL=https://your-domain.atlassian.net/wiki
MCP_BEARER_TOKEN=your-token
```

## 📊 Agent Architecture

### Supervisor-Led Workflow

The system uses a **supervisor-led LangGraph workflow** with 7 specialized agents:

1. **Orchestrator/Supervisor** - Controls workflow and state transitions
2. **Context Retrieval Agent** - Fetches context from MCP
3. **Extraction Agent** - Extracts technical facts
4. **Questionnaire Agent** - Identifies gaps and generates questions
5. **Intake Draft Agent** - Creates structured intake document
6. **Review/Validation Agent** - Validates completeness and consistency
7. **Migration Planning Agent** - Generates migration strategy and plan

### State Management

**Transactional ACID Properties:**
- **Atomicity**: All-or-nothing commits with exclusive locks
- **Consistency**: Schema validation and phase transition rules
- **Isolation**: Single writer lock with optimistic locking
- **Durability**: Checkpoints and write-ahead logging

## 🧪 Testing

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run with markers
pytest -m unit
pytest -m integration
```

## 📈 Observability

### LangSmith Tracing

Every operation is traced:
- MCP requests
- LLM calls
- Agent executions
- State transitions
- Validation steps

Access traces at: https://smith.langchain.com

### Metrics (Future)

Prometheus metrics exposed at `/metrics`:
- Request latency
- Provider health
- Token usage
- Error rates

## 🔐 Security

- Non-root container user
- API key validation
- CORS configuration
- Input validation with Pydantic
- Rate limiting (future)

## 📝 Development Phases

- ✅ **Phase 1**: Foundation (Configuration, Providers, Tracing)
- 🚧 **Phase 2**: MCP Connector
- 🚧 **Phase 3**: LangGraph Orchestration
- 🚧 **Phase 4**: Core Agents
- 🚧 **Phase 5**: Intake & Review
- 🚧 **Phase 6**: Migration Planning
- 🚧 **Phase 7**: Frontend UI
- 🚧 **Phase 8**: Deployment & Observability

## 🤝 Contributing

This is a POC project. For production use:
1. Add authentication/authorization
2. Implement rate limiting
3. Add comprehensive error handling
4. Set up CI/CD pipelines
5. Add monitoring and alerting
6. Implement data persistence
7. Add audit logging

## 📄 License

[Your License Here]

## 🆘 Support

For issues and questions:
- Check documentation in `docs/`
- Review API docs at `/docs`
- Check LangSmith traces for debugging

## 🎯 Success Criteria

The POC is successful if:
- ✅ MCP retrieval is configurable and plug-and-play
- ✅ Agents can request different context slices through profiles
- ✅ State transitions are deterministic and traceable
- ✅ Shared state updates are transaction-like and safe
- ✅ LangSmith clearly shows workflow execution
- ✅ Intake draft can be created and reviewed
- ✅ Migration plan can be generated from reviewed intake
- ✅ UI and backend feel coherent and demo-ready