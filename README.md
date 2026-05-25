# Migration Agent Orchestration POC

Enterprise Application Modernization Copilot - A LangGraph-based multi-agent orchestration system for automated migration planning.

## Overview

This POC implements an intelligent agent orchestration system that automates the application migration planning process by:

- Ingesting Confluence pages and uploaded documents
- Fetching context using configurable MCP connectors
- Extracting migration-relevant facts with confidence scoring
- Generating questionnaire gaps for missing information
- Drafting comprehensive intake documents
- Supporting human review and approval workflows
- Generating migration plans with cloud infrastructure recommendations
- Providing transparent execution traces using LangSmith

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│              FastAPI + LangGraph + Agents                    │
└────────┬────────────────────────────┬────────────────────────┘
         │                            │
         │                            │
    ┌────▼─────────┐          ┌──────▼──────────┐
    │  LangSmith   │          │  Prometheus     │
    │  (LLM Trace) │          │  (Metrics)      │
    └──────────────┘          └──────┬──────────┘
                                     │
                              ┌──────▼──────────┐
                              │    Grafana      │
                              │  (Dashboard)    │
                              └─────────────────┘
```

## Tech Stack

### Backend
- **FastAPI**: REST API framework
- **LangGraph**: Multi-agent workflow orchestration
- **LangSmith**: LLM tracing and observability
- **OpenAI + Gemini**: LLM providers with automatic fallback
- **Redis**: Caching and state persistence
- **Qdrant**: Vector store for semantic search

### Frontend
- **React**: UI framework
- **IBM Carbon Design System**: Enterprise UI components

### Infrastructure
- **Podman**: Container runtime
- **Prometheus**: Metrics collection
- **Grafana**: Visualization and dashboards

## Key Features

### 1. Transactional State Management
- Optimistic locking with version control
- Write-ahead logging (changelog)
- Atomic state updates
- Rollback capability

### 2. Multi-Agent Orchestration
- **Supervisor Agent**: Workflow routing and control
- **Context Retrieval Agent**: Document fetching and normalization
- **Extraction Agent**: Technical fact extraction with confidence scoring
- **Questionnaire Agent**: Gap identification and question generation
- **Intake Draft Agent**: Document synthesis and generation
- **Review Agent**: Quality validation and contradiction detection
- **Migration Planning Agent**: Strategy and cloud recommendations

### 3. Human-in-the-Loop
- Review checkpoints before critical decisions
- State updates during workflow pause
- Approval workflows with audit trails

### 4. Complete Observability
- LangSmith tracing for all LLM calls and agent decisions
- Prometheus metrics for system performance
- Grafana dashboards for unified monitoring
- Cost tracking and optimization

### 5. Plug-and-Play Architecture
- Configurable MCP connectors (Confluence Cloud)
- Provider abstraction (OpenAI/Gemini with fallback)
- Retrieval profiles for different agent needs
- No hardcoded dependencies

## Project Structure

```
mig-26/
├── .agents/
│   └── langgraph-skills/
│       ├── fastapi-skill/
│       └── langgraph-skill/
├── docs/
│   ├── 00-architecture-overview.md
│   ├── 01-phase1-foundation.md
│   ├── 03-phase3-orchestration.md
│   ├── 09-single-point-of-failure-analysis.md
│   ├── 11-observability-stack.md
│   ├── 12-agent-orchestration-analysis.md
│   └── 13-langsmith-tracing-setup.md
├── backend/                    # (To be implemented)
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── providers/
│   │   ├── orchestration/
│   │   ├── agents/
│   │   ├── mcp/
│   │   └── tracing/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                   # (To be implemented)
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── monitoring/                 # (To be implemented)
│   ├── prometheus.yml
│   └── grafana/
├── .gitignore
├── README.md
└── podman-compose.yml         # (To be implemented)
```

## Documentation

### Core Documentation

1. **[Architecture Overview](docs/00-architecture-overview.md)** - System architecture and design principles
2. **[Agent Orchestration Analysis](docs/12-agent-orchestration-analysis.md)** - Deep-dive into agent design, prompts, and decision-making
3. **[SPOF Analysis](docs/09-single-point-of-failure-analysis.md)** - Single point of failure mitigation strategies
4. **[Observability Stack](docs/11-observability-stack.md)** - Complete monitoring setup (LangSmith + Prometheus + Grafana)
5. **[LangSmith Tracing Setup](docs/13-langsmith-tracing-setup.md)** - LangSmith configuration and usage guide

### Implementation Phases

1. **[Phase 1: Foundation](docs/01-phase1-foundation.md)** - Project skeleton, FastAPI backend, provider abstraction, LangSmith setup
2. **[Phase 2: MCP Connector](docs/02-phase2-mcp-connector.md)** - Configurable MCP connector, document parsing, vector store, context normalization
3. **[Phase 3: Orchestration](docs/03-phase3-orchestration.md)** - LangGraph workflow, transactional state management, checkpointing
4. **[Phase 4: Core Agents](docs/04-phase4-core-agents.md)** - Context Retrieval, Extraction, and Questionnaire agents
5. **[Phase 5: Intake & Review](docs/05-phase5-intake-review.md)** - Intake Draft and Review agents with human-in-the-loop
6. **[Phase 6: Migration Planning](docs/06-phase6-migration-planning.md)** - Migration Planning agent with cloud recommendations
7. **[Phase 7: Frontend UI](docs/07-phase7-frontend-ui.md)** - React application with IBM Carbon Design System
8. **[Phase 8: Testing & Demo](docs/08-phase8-testing-demo.md)** - Integration testing, performance testing, and demo preparation

### Skills

- **[FastAPI Skill](.agents/langgraph-skills/fastapi-skill/SKILL.md)** - FastAPI best practices
- **[LangGraph Skill](.agents/langgraph-skills/langgraph-skill/SKILL.md)** - LangGraph patterns and conventions

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Podman or Docker
- OpenAI API key
- Google Gemini API key
- LangSmith API key
- Confluence Cloud access

### Environment Setup

1. Clone the repository:
```bash
git clone https://github.ibm.com/poc-org-bob/migration-agent-orchestartion.git
cd migration-agent-orchestartion
```

2. Create `.env` file:
```bash
# LLM Providers
PRIMARY_PROVIDER=openai
FALLBACK_PROVIDER=gemini
OPENAI_API_KEY=your-openai-key
GEMINI_API_KEY=your-gemini-key

# LangSmith
LANGSMITH_API_KEY=your-langsmith-key
LANGSMITH_PROJECT=migration-copilot-poc
LANGSMITH_TRACING=true

# MCP/Confluence
CONFLUENCE_URL=https://your-instance.atlassian.net
CONFLUENCE_USERNAME=your-email@company.com
CONFLUENCE_API_TOKEN=your-confluence-token
```

3. Start services (when implemented):
```bash
podman-compose up -d
```

4. Access services:
- Backend API: http://localhost:8000
- Frontend UI: http://localhost:3000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001
- LangSmith: https://smith.langchain.com

## Development Phases

### ✅ Phase 0: Planning (Complete)
- Architecture design
- Agent orchestration analysis
- Observability strategy
- Documentation

### 🔄 Phase 1: Foundation (Next)
- Project skeleton
- FastAPI backend
- Provider abstraction
- LangSmith integration
- Podman setup

### 📋 Phase 2: MCP Connector
- Confluence Cloud integration
- Document parsing
- Vector store setup
- Context normalization

### 📋 Phase 3: Orchestration
- LangGraph workflow
- Transactional state manager
- Checkpointing
- Error handling

### 📋 Phase 4: Core Agents
- Context Retrieval Agent
- Extraction Agent
- Questionnaire Agent

### 📋 Phase 5: Intake & Review
- Intake Draft Agent
- Review/Validation Agent
- Human review UI

### 📋 Phase 6: Migration Planning
- Migration Planning Agent
- Final validation
- Output generation

### 📋 Phase 7: Frontend UI
- React application
- IBM Carbon components
- Dashboard and viewers

### 📋 Phase 8: Testing
- Integration tests
- Demo preparation
- Documentation

## Key Design Decisions

### 1. Supervisor Pattern
- Centralized workflow control
- Deterministic routing
- No direct agent-to-agent communication

### 2. Transactional State
- Optimistic locking prevents concurrent writes
- Version-based conflict detection
- Write-ahead logging for audit trail

### 3. Provider Abstraction
- OpenAI as primary, Gemini as fallback
- Circuit breaker pattern
- Automatic failover

### 4. Caching Strategy
- LLM response caching (90% cost reduction)
- MCP context caching (10-20x faster)
- Embedding caching (instant retrieval)

### 5. Hybrid Validation
- Rule-based checks for obvious issues
- LLM-based checks for semantic issues
- Best cost/quality balance

## Cost Optimization

- **Caching**: 90% cost reduction on repeated queries
- **Batch Processing**: Combine documents in single calls
- **Model Selection**: Cheaper models for simple tasks
- **Prompt Optimization**: Shorter, focused prompts
- **Structured Output**: JSON mode reduces tokens

## Monitoring

### Metrics Tracked
- LLM request rate and latency
- Cache hit/miss rates
- Token usage and costs
- Workflow execution times
- State transaction success rates
- System resources (CPU, memory)

### Alerts
- High LLM error rate
- Low cache hit rate
- High LLM cost
- State transaction failures
- Slow workflow phases

## Security

- API keys in environment variables
- Bearer token authentication for MCP
- No persistent storage of sensitive data (POC)
- Complete audit trail via changelog
- Input validation with Pydantic

## Contributing

This is a POC project. For contributions:

1. Follow the documented architecture
2. Use the provided skills for FastAPI and LangGraph
3. Maintain transactional state management patterns
4. Add LangSmith tracing for new operations
5. Update documentation

## License

IBM Internal POC - Proprietary

## Contact

- **Project**: Migration Agent Orchestration POC
- **Organization**: poc-org-bob
- **Repository**: https://github.ibm.com/poc-org-bob/migration-agent-orchestartion

## Acknowledgments

- LangChain/LangGraph for orchestration framework
- IBM Carbon Design System for UI components
- OpenAI and Google for LLM capabilities
- LangSmith for observability platform