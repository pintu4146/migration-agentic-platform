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

- Python 3.10+
- Podman or Docker (optional, for containerized deployment)
- OpenAI API key
- (Optional) Google Gemini API key
- (Optional) LangSmith API key
- (Optional) Confluence Cloud access

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