# 🚀 IBM Migration Copilot

## Intelligent Application Modernization Through Agentic AI

> **Transform legacy application migration from weeks of manual analysis to hours of AI-powered intelligence.**

The IBM Migration Copilot is an enterprise-grade **Agentic AI application** that revolutionizes the application modernization process by automatically analyzing AS-IS infrastructure, generating comprehensive intake documentation with intelligent questionnaires, and producing actionable cloud migration plans.

---

## 🎯 What Problem Does This Solve?

Traditional application migration requires:
- ❌ **Weeks of manual document analysis** across scattered Confluence pages, configuration files, and technical specs
- ❌ **Inconsistent intake documentation** with missing critical details
- ❌ **Repetitive questionnaires** that fail to capture application-specific nuances
- ❌ **Delayed migration planning** due to incomplete AS-IS understanding

### ✅ The IBM Migration Copilot Solution

Our AI-powered copilot **automatically**:
1. **Ingests** project configuration files (pom.xml, build.gradle, application.properties, .env) and Confluence documentation
2. **Extracts** migration-relevant facts about tech stack, dependencies, runtime configuration, and architectural decisions
3. **Generates** intelligent questionnaires with context-aware questions to fill knowledge gaps
4. **Drafts** comprehensive intake documents with AS-IS state, dependencies, constraints, and risks
5. **Enables** human review and validation through an intuitive UI
6. **Produces** detailed migration plans with cloud infrastructure recommendations and phased execution strategies

---

## 🏗️ Architecture Highlights

### Multi-Agent Orchestration with LangGraph

The copilot employs a **supervisor-led agent team** where each agent has specialized responsibilities:

| Agent | Responsibility |
|-------|---------------|
| **Orchestrator/Supervisor** | Controls workflow, manages phase transitions, validates state updates |
| **Context Retrieval Agent** | Fetches and normalizes content from MCP connectors and uploaded files |
| **Extraction Agent** | Extracts technical facts with confidence scoring and evidence tracking |
| **Questionnaire Agent** | Identifies knowledge gaps and generates prioritized questions |
| **Intake Draft Agent** | Produces structured intake documents ready for human review |
| **Review/Validation Agent** | Checks for contradictions, unsupported claims, and completeness |
| **Migration Planning Agent** | Recommends migration strategies with cloud infrastructure solutions |

### Transaction-Style State Management

- **LangGraph State Reducers**: Built-in `merge_lists` and `merge_dicts` for automatic conflict resolution
- **Deterministic Workflow**: Every state transition is traceable and reproducible
- **Safe Concurrent Updates**: Type-safe state patches prevent data corruption
- **State Synchronization**: LangGraph in-memory state synced to Redis for real-time UI updates

### Plug-and-Play Knowledge Retrieval

- **Configurable MCP Connector**: Supports multiple knowledge sources (Confluence, SharePoint, etc.)
- **Retrieval Profiles**: Each agent can request different context slices (extraction_profile, questionnaire_profile, planning_profile)
- **Evidence Tracking**: Every extracted fact links back to source documents with page/line references
- **Multi-Format Parsing**: Supports PDF, DOCX, Excel, XML, Markdown, Properties, and plain text

### Enterprise-Grade Observability

- **LangSmith Tracing**: Every node execution, tool call, and state transition is traced
- **Real-Time Streaming**: Server-Sent Events (SSE) provide live workflow updates to the UI
- **Transparent Decision Making**: See exactly how the AI moved from source documents to final recommendations
- **Audit Trail**: Complete changelog of state diffs for compliance and debugging

---

## 🛠️ Technology Stack

### Frontend
- **React** with **IBM Carbon Design System** for enterprise-grade UI/UX
- Real-time SSE streaming for live workflow updates
- Structured data viewers for facts, questionnaires, and migration plans

### Backend
- **FastAPI** for high-performance async API
- **LangGraph** for multi-agent orchestration
- **OpenAI** (primary) and **Gemini** (fallback) with provider abstraction
- **Redis** for state synchronization and caching
- **Qdrant** for vector storage and semantic search

### Parsing & Ingestion
- **PyMuPDF**, **python-docx**, **pandas**, **openpyxl** for multi-format document parsing
- **Sentence Transformers** for embeddings
- **MCP Protocol** for plug-and-play knowledge source integration

### Container Runtime
- **Podman** for lightweight, secure containerization
- **Podman Compose** for multi-container orchestration

---

## 📋 Prerequisites

Before starting, ensure you have:

1. **Python 3.11+** installed
2. **Node.js 18+** and npm installed
3. **Podman** installed and running
4. **Git** for version control

### API Keys Required

Set these environment variables:

```bash
# LLM Providers (at least one required)
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_gemini_key_here  # Optional fallback

# Observability
LANGSMITH_API_KEY=your_langsmith_key_here
LANGSMITH_PROJECT=migration-copilot-poc

# MCP Connector (if using Confluence)
MCP_BASE_URL=https://your-confluence-instance.com
MCP_BEARER_TOKEN=your_confluence_token_here
```

---

## 🚀 Quick Start Guide

### Step 1: Clone and Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd mig-26

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
notepad .env  # Windows
nano .env     # Linux/Mac
```

### Step 2: Start Container Services

```bash
# Start Redis and Qdrant containers
cd backend
podman-compose up -d

# Verify containers are running
podman ps
```

Expected output:
```
CONTAINER ID  IMAGE                              STATUS
<id>          docker.io/library/redis:7-alpine   Up
<id>          docker.io/qdrant/qdrant:latest     Up
```

### Step 3: Setup Backend

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate  # Windows
source venv/bin/activate # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: `http://localhost:8000`

### Step 4: Setup Frontend

```bash
# Open new terminal
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: `http://localhost:5173`

### Step 5: Create Your First Project

1. Navigate to `http://localhost:5173`
2. Click **"Create New Project"**
3. Enter project details (name, description)
4. Upload configuration files:
   - `pom.xml` or `build.gradle` (build configuration)
   - `application.properties` or `.env` (runtime configuration)
   - Any relevant documentation (PDF, DOCX, Markdown)
5. Optionally connect Confluence pages via MCP

### Step 6: Start the Workflow

1. Click **"Start Workflow"** on the dashboard
2. Watch real-time progress as agents:
   - Retrieve and normalize context
   - Extract technical facts
   - Generate questionnaires
   - Draft intake document
3. Review extracted facts and questionnaires
4. Approve or modify the intake draft
5. Generate migration plan with cloud recommendations

### Step 7: Review and Export

1. Navigate to **"Human Review"** page
2. Review:
   - **Intake Draft**: Comprehensive AS-IS state summary
   - **Validation Results**: Completeness and consistency checks
   - **Review Flags**: Items requiring attention
3. Approve the intake document
4. View the generated **Migration Plan** with:
   - Recommended migration strategy
   - Phased execution plan
   - Cloud infrastructure recommendations
   - Risk assessment and rollback procedures

---

## 📊 Key Features

### 🔍 Intelligent Context Extraction

- **Multi-Source Ingestion**: Confluence pages, uploaded files, and MCP-connected knowledge bases
- **Smart Parsing**: Automatically detects and parses 8+ file formats
- **Evidence Linking**: Every extracted fact references source documents with page/line numbers
- **Confidence Scoring**: AI assigns confidence levels to extracted information

### 📝 Dynamic Questionnaire Generation

- **Gap Analysis**: Identifies missing or weakly supported information
- **Prioritized Questions**: Ranks questions by importance and impact
- **Context-Aware**: Questions are tailored to the specific application stack
- **Evidence Mapping**: Links questions to missing evidence for targeted follow-up

### 📄 Comprehensive Intake Documentation

- **Structured Format**: Consistent intake document structure across all projects
- **AS-IS State Summary**: Current architecture, tech stack, and deployment model
- **Dependencies & Constraints**: External systems, compliance requirements, and limitations
- **Risk Assessment**: Identified risks with severity levels and mitigation strategies
- **Open Questions**: Clearly flagged items requiring human input

### 🔄 Human-in-the-Loop Review

- **Intuitive UI**: IBM Carbon Design System for familiar enterprise experience
- **Real-Time Updates**: SSE streaming shows workflow progress live
- **Validation Checks**: Automated consistency and completeness validation
- **Approval Workflow**: Human review gate before migration planning

### ☁️ Cloud Migration Planning

- **Strategy Recommendations**: Rehost, Replatform, Refactor, or Hybrid approaches
- **Infrastructure Mapping**: Specific cloud services for each application component
- **Phased Execution**: Step-by-step migration plan with dependencies
- **Rollback Procedures**: Safety measures and contingency plans

### 🔬 Full Observability

- **LangSmith Integration**: Trace every agent decision and LLM call
- **State Changelog**: Complete audit trail of workflow state changes
- **Debug Panel**: In-UI access to trace metadata and execution logs
- **Performance Metrics**: Track agent execution times and token usage

---

## 🏢 Enterprise-Ready Features

### Security & Compliance

- **No Data Persistence**: POC uses in-memory/ephemeral storage (production-ready architecture documented)
- **API Key Management**: Environment-based credential management
- **Audit Logging**: Complete traceability of all operations
- **Role-Based Access**: (Planned for production)

### Scalability

- **Async Architecture**: FastAPI with async/await for high concurrency
- **Container-Based**: Easy horizontal scaling with Podman/Kubernetes
- **Vector Store**: Qdrant for efficient semantic search at scale
- **State Management**: Redis for distributed state synchronization

### Extensibility

- **Provider Abstraction**: Easily swap OpenAI for Gemini or other LLM providers
- **MCP Protocol**: Plug-and-play knowledge source connectors
- **Retrieval Profiles**: Configurable context retrieval per agent
- **Custom Parsers**: Add new file format parsers without changing core logic

---

## 🧪 Testing & Validation

### Run Backend Tests

```bash
cd backend
pytest -v
```

### Run Frontend Tests

```bash
cd frontend
npm test
```

### Manual Testing Checklist

- [ ] Create project and upload files
- [ ] Start workflow and verify context retrieval
- [ ] Check extracted facts for accuracy
- [ ] Review generated questionnaires
- [ ] Validate intake draft completeness
- [ ] Approve intake and generate migration plan
- [ ] Verify LangSmith traces are captured

---

## 🐛 Troubleshooting

### Containers Not Starting

```bash
# Check Podman status
podman ps -a

# View container logs
podman logs <container-id>

# Restart containers
podman-compose down
podman-compose up -d
```

### Backend Connection Issues

```bash
# Verify Redis connection
python backend/check_redis.ps1

# Check backend logs
# Look for startup errors in terminal running uvicorn
```

### Frontend Not Loading

```bash
# Clear npm cache
npm cache clean --force

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Check for port conflicts
netstat -ano | findstr :5173  # Windows
lsof -i :5173                 # Linux/Mac
```

### LangSmith Traces Not Appearing

1. Verify `LANGSMITH_API_KEY` is set in `.env`
2. Check `LANGSMITH_PROJECT` matches your LangSmith project name
3. Ensure `LANGCHAIN_TRACING_V2=true` in `.env`
4. Check backend logs for LangSmith connection errors

---

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- **Architecture Overview**: `docs/00-architecture-overview.md`
- **Phase-Wise Implementation**: `docs/phase-wise/`
- **Workflow Details**: `docs/workflow/`
- **Fix Documentation**: `docs/fixes/`
- **Observability Setup**: `docs/11-observability-stack.md`

---

## 🎯 Success Criteria

This POC demonstrates:

✅ **Plug-and-Play Knowledge Retrieval**: MCP connector supports multiple sources with configurable profiles  
✅ **Intelligent Agent Orchestration**: 7 specialized agents with clear boundaries and responsibilities  
✅ **Transaction-Style State Management**: LangGraph reducers ensure deterministic, traceable state updates  
✅ **Human-in-the-Loop Review**: Intuitive UI for reviewing and approving AI-generated content  
✅ **Transparent Execution**: LangSmith tracing shows complete decision-making process  
✅ **Enterprise UI/UX**: IBM Carbon Design System for familiar, trustworthy interface  
✅ **Multi-Provider Support**: OpenAI primary, Gemini fallback with common abstraction  

---

## 🚧 Known Limitations (POC Scope)

- **In-Memory Storage**: State and vectors are ephemeral (production would use persistent databases)
- **Single-User**: No authentication or multi-tenancy (production-ready architecture documented)
- **Limited Migration Planning**: Phase 6 agent is placeholder (full implementation planned)
- **Dependency Vulnerabilities**: 43 third-party package vulnerabilities (acceptable for POC, remediation plan documented)

---

## 🔮 Future Enhancements

### Phase 6: Migration Planning Agent (In Progress)
- Complete migration strategy recommendation engine
- Cloud infrastructure cost estimation
- Detailed phased execution plans with timelines

### Phase 8: End-to-End Testing & Demo
- Comprehensive integration tests
- Demo scenarios with sample projects
- Performance benchmarking

### Production Readiness
- Persistent database (PostgreSQL)
- Persistent vector store (Qdrant Cloud)
- Authentication & authorization (OAuth2/OIDC)
- Multi-tenancy support
- Dependency vulnerability remediation
- Kubernetes deployment manifests

---

## 📞 Support & Contribution

For questions, issues, or contributions:

1. Check existing documentation in `docs/`
2. Review troubleshooting section above
3. Check LangSmith traces for workflow debugging
4. Contact the development team

---

## 📄 License

[Add your license information here]

---

## 🙏 Acknowledgments

Built with:
- **LangGraph** for agent orchestration
- **LangSmith** for observability
- **IBM Carbon Design System** for enterprise UI
- **FastAPI** for high-performance backend
- **OpenAI** and **Google Gemini** for LLM capabilities

---

**IBM Migration Copilot** - Transforming Application Modernization Through Intelligent Automation 🚀