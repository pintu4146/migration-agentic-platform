# Phase 8: Integration Testing & Demo Preparation

## Overview

Phase 8 focuses on comprehensive integration testing, demo preparation, and final system validation. This phase ensures the entire system works end-to-end and is ready for demonstration to stakeholders.

## Objectives

1. **Integration Testing**
   - End-to-end workflow testing
   - API integration testing
   - Agent orchestration testing
   - State management testing
   - Error handling validation

2. **Performance Testing**
   - Load testing
   - Response time validation
   - Resource utilization monitoring
   - Cost optimization verification

3. **Demo Preparation**
   - Sample data creation
   - Demo script development
   - Walkthrough documentation
   - Troubleshooting guide

4. **Documentation Finalization**
   - API documentation
   - Deployment guide
   - User guide
   - Architecture documentation

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Testing Framework                         │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Integration Tests                          │ │
│  │  - End-to-end workflow                                  │ │
│  │  - API endpoints                                        │ │
│  │  - Agent orchestration                                  │ │
│  │  - State management                                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │            Performance Tests                            │ │
│  │  - Load testing (Locust)                                │ │
│  │  - Response time monitoring                             │ │
│  │  - Resource profiling                                   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Demo Environment                           │ │
│  │  - Sample Confluence pages                              │ │
│  │  - Pre-configured profiles                              │ │
│  │  - Demo walkthrough script                              │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

## Implementation

### 1. End-to-End Integration Tests

```python
# tests/integration/test_e2e_workflow.py
import pytest
import asyncio
from datetime import datetime

from backend.app.orchestration.workflow import MigrationWorkflow
from backend.app.orchestration.state_manager import StateManager
from backend.app.mcp.connector import MCPConnector
from backend.app.llm.provider import LLMProvider

@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_workflow():
    """
    Test complete workflow from context retrieval to migration plan.
    
    This test validates:
    - Context retrieval from MCP
    - Fact extraction
    - Question generation
    - Intake draft creation
    - Human review simulation
    - Migration plan generation
    - State management throughout
    """
    
    # Initialize components
    state_manager = StateManager()
    llm_provider = LLMProvider(provider="openai")
    mcp_connector = MCPConnector(config=test_mcp_config)
    
    # Initialize workflow
    workflow = MigrationWorkflow(
        state_manager=state_manager,
        llm_provider=llm_provider,
        mcp_connector=mcp_connector
    )
    
    # Create project
    project_id = f"test_project_{datetime.utcnow().timestamp()}"
    state = await state_manager.initialize_state(project_id)
    
    assert state["phase"] == "INIT"
    assert state["state_version"] == 0
    
    # Phase 1: Context Retrieval
    state = await workflow.execute_phase("context_retrieval", state)
    
    assert state["phase"] == "EXTRACTION"
    assert state["context_pack"] is not None
    assert len(state["normalized_docs"]) > 0
    assert state["state_version"] == 1
    
    # Phase 2: Extraction
    state = await workflow.execute_phase("extraction", state)
    
    assert state["phase"] == "QUESTIONNAIRE"
    assert state["extracted_facts"] is not None
    assert state["confidence_scores"] is not None
    assert state["evidence_map"] is not None
    assert state["state_version"] == 2
    
    # Phase 3: Questionnaire
    state = await workflow.execute_phase("questionnaire", state)
    
    assert state["phase"] == "INTAKE_DRAFT"
    assert len(state["missing_questions"]) > 0
    assert state["question_priorities"] is not None
    assert state["state_version"] == 3
    
    # Phase 4: Intake Draft
    state = await workflow.execute_phase("intake_draft", state)
    
    assert state["phase"] == "HUMAN_REVIEW"
    assert state["intake_draft"] is not None
    assert "document_text" in state["intake_draft"]
    assert state["state_version"] == 4
    
    # Phase 5: Review/Validation
    state = await workflow.execute_phase("review", state)
    
    assert state["validation_results"] is not None
    assert "review_flags" in state
    assert state["state_version"] == 5
    
    # Simulate human review approval
    state = await workflow.approve_human_review(
        state,
        comments=["Looks good", "Approved for migration planning"],
        approved=True
    )
    
    assert state["human_reviewed"] == True
    assert state["phase"] == "MIGRATION_PLANNING"
    assert state["state_version"] == 6
    
    # Phase 6: Migration Planning
    state = await workflow.execute_phase("migration_planning", state)
    
    assert state["phase"] == "VALIDATION"
    assert state["migration_plan"] is not None
    assert "strategy" in state["migration_plan"]
    assert "phases" in state["migration_plan"]
    assert "cloud_recommendations" in state["migration_plan"]
    assert state["state_version"] == 7
    
    # Phase 7: Final Validation
    state = await workflow.execute_phase("final_validation", state)
    
    assert state["phase"] == "COMPLETE"
    assert state["validation_results"]["is_valid"] == True
    assert state["state_version"] == 8
    
    # Verify state changelog
    assert len(state["state_changelog"]) == 8
    
    # Verify trace metadata
    assert "context_retrieval" in state["trace_metadata"]
    assert "extraction" in state["trace_metadata"]
    assert "questionnaire" in state["trace_metadata"]
    assert "intake_draft" in state["trace_metadata"]
    assert "validation" in state["trace_metadata"]
    assert "migration_planning" in state["trace_metadata"]

@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow_with_rejection():
    """Test workflow with human review rejection and iteration"""
    
    # ... setup ...
    
    # Execute up to human review
    state = await workflow.execute_until_phase("HUMAN_REVIEW", state)
    
    # Simulate rejection
    state = await workflow.approve_human_review(
        state,
        comments=["Missing database details", "Need more information on authentication"],
        approved=False
    )
    
    assert state["human_reviewed"] == False
    assert state["phase"] == "INTAKE_DRAFT"
    assert state["retry_count"] == 1
    
    # Re-execute intake draft with additional context
    state = await workflow.execute_phase("intake_draft", state)
    
    assert state["phase"] == "HUMAN_REVIEW"
    assert state["retry_count"] == 1

@pytest.mark.integration
@pytest.mark.asyncio
async def test_error_recovery():
    """Test error handling and recovery"""
    
    # ... setup ...
    
    # Simulate error during extraction
    with pytest.raises(Exception):
        state = await workflow.execute_phase("extraction", invalid_state)
    
    # Verify error logged
    assert len(state["error_log"]) > 0
    assert state["phase"] == "ERROR"
    
    # Recover from checkpoint
    recovered_state = await state_manager.recover_from_checkpoint(
        version=state["state_version"] - 1
    )
    
    assert recovered_state["phase"] != "ERROR"
```

### 2. API Integration Tests

```python
# tests/integration/test_api_endpoints.py
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

@pytest.mark.integration
def test_project_creation():
    """Test project creation endpoint"""
    
    response = client.post(
        "/api/projects",
        json={
            "name": "Test Migration Project",
            "description": "Integration test project"
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "project_id" in data
    assert data["phase"] == "INIT"

@pytest.mark.integration
def test_context_retrieval():
    """Test context retrieval endpoint"""
    
    # Create project
    project_response = client.post("/api/projects", json={"name": "Test"})
    project_id = project_response.json()["project_id"]
    
    # Trigger context retrieval
    response = client.post(
        f"/api/projects/{project_id}/retrieve-context",
        json={
            "profile": "context_retrieval",
            "space_keys": ["TEST"]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["phase"] == "EXTRACTION"
    assert "context_pack" in data

@pytest.mark.integration
def test_human_review_workflow():
    """Test human review submission"""
    
    # ... setup project and execute to review phase ...
    
    # Get intake draft
    response = client.get(f"/api/review/intake/{project_id}")
    assert response.status_code == 200
    
    # Submit review
    response = client.post(
        "/api/review/submit",
        json={
            "project_id": project_id,
            "approved": True,
            "comments": ["Approved"]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["next_phase"] == "MIGRATION_PLANNING"

@pytest.mark.integration
def test_migration_plan_export():
    """Test migration plan export"""
    
    # ... setup project and execute to completion ...
    
    # Export as PDF
    response = client.get(f"/api/plan/{project_id}/export/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    
    # Export as JSON
    response = client.get(f"/api/plan/{project_id}/export/json")
    assert response.status_code == 200
    data = response.json()
    assert "migration_plan" in data
```

### 3. Performance Tests

```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between

class MigrationCopilotUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Create project on start"""
        response = self.client.post(
            "/api/projects",
            json={"name": f"Load Test Project {self.user_id}"}
        )
        self.project_id = response.json()["project_id"]
    
    @task(3)
    def get_project_status(self):
        """Get project status (most common operation)"""
        self.client.get(f"/api/projects/{self.project_id}/status")
    
    @task(2)
    def get_intake_draft(self):
        """Get intake draft"""
        self.client.get(f"/api/review/intake/{self.project_id}")
    
    @task(1)
    def get_migration_plan(self):
        """Get migration plan"""
        self.client.get(f"/api/plan/{self.project_id}")

# Run with: locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

### 4. Demo Data Setup

```python
# scripts/setup_demo_data.py
import asyncio
from backend.app.orchestration.state_manager import StateManager
from backend.app.mcp.connector import MCPConnector

async def setup_demo_project():
    """
    Create a demo project with pre-populated data.
    
    This creates a realistic demo scenario with:
    - Sample Confluence pages
    - Extracted facts
    - Generated questions
    - Draft intake document
    - Ready for human review
    """
    
    state_manager = StateManager()
    
    # Create demo project
    state = await state_manager.initialize_state("demo_project_001")
    
    # Add sample context
    demo_context = {
        "pages": [
            {
                "id": "demo_page_1",
                "title": "Application Architecture",
                "content": """
                # E-Commerce Platform Architecture
                
                ## Technology Stack
                - Java 11
                - Spring Boot 2.7
                - PostgreSQL 13
                - Redis 6.2
                - React 18
                
                ## Current Deployment
                - Deployed on on-premise servers
                - 3 application servers (load balanced)
                - 1 primary database, 1 read replica
                - Redis for session management
                
                ## Known Issues
                - Scaling challenges during peak traffic
                - Manual deployment process
                - Limited monitoring capabilities
                """
            },
            {
                "id": "demo_page_2",
                "title": "Security & Compliance",
                "content": """
                # Security Configuration
                
                ## Authentication
                - OAuth 2.0 with JWT tokens
                - Session timeout: 30 minutes
                
                ## Data Encryption
                - TLS 1.2 for data in transit
                - AES-256 for sensitive data at rest
                
                ## Compliance
                - PCI DSS Level 1 compliant
                - GDPR compliant
                """
            }
        ],
        "attachments": []
    }
    
    # Commit context
    await state_manager.commit_state_patch(
        patch={
            "context_pack": demo_context,
            "normalized_docs": normalize_demo_context(demo_context),
            "phase": "EXTRACTION"
        },
        expected_version=0,
        committed_by="demo_setup"
    )
    
    print(f"✅ Demo project created: demo_project_001")
    print(f"   Phase: EXTRACTION")
    print(f"   Ready for demonstration")

if __name__ == "__main__":
    asyncio.run(setup_demo_project())
```

### 5. Demo Script

```markdown
# Migration Copilot Demo Script

## Preparation (5 minutes before demo)

1. Start all services:
   ```bash
   docker-compose up -d
   ```

2. Verify services are running:
   - Backend: http://localhost:8000/health
   - Frontend: http://localhost:3000
   - LangSmith: Check trace dashboard

3. Load demo data:
   ```bash
   python scripts/setup_demo_data.py
   ```

## Demo Flow (20 minutes)

### Part 1: Introduction (2 minutes)

**Script:**
"Today I'll demonstrate our AI-powered migration copilot that automates the analysis and planning of application migrations to the cloud. The system uses a multi-agent architecture with LangGraph to orchestrate the workflow."

**Show:**
- Architecture diagram
- Key features slide

### Part 2: Dashboard & Workflow (3 minutes)

**Script:**
"Let's start with the dashboard. Here you can see the current project status and workflow progress."

**Actions:**
1. Navigate to http://localhost:3000/dashboard
2. Point out:
   - Current phase indicator
   - Progress tracker
   - Project metadata

**Key Points:**
- 7-phase workflow
- Transactional state management
- Human-in-the-loop review

### Part 3: Context Retrieval (3 minutes)

**Script:**
"The system starts by retrieving context from Confluence and uploaded documents. We use a configurable MCP connector that supports multiple retrieval profiles."

**Actions:**
1. Navigate to Context Viewer
2. Show retrieved Confluence pages
3. Highlight:
   - Source tracking
   - Evidence preservation
   - Document normalization

**Key Points:**
- Plug-and-play MCP connector
- Multiple source types supported
- Normalized JSON output

### Part 4: Fact Extraction (4 minutes)

**Script:**
"Next, our extraction agent uses an LLM to parse the unstructured context and extract migration-relevant facts. Each fact includes a confidence score and evidence reference."

**Actions:**
1. Navigate to Facts Viewer
2. Show extracted facts by category:
   - Technical Stack
   - Dependencies
   - Security & Compliance
3. Click on a fact to show evidence

**Key Points:**
- LLM-based extraction
- Confidence scoring
- Evidence mapping
- Structured output

### Part 5: Gap Analysis & Questions (3 minutes)

**Script:**
"The questionnaire agent identifies information gaps and generates prioritized questions. High-priority questions block migration planning."

**Actions:**
1. Navigate to Questions page
2. Show prioritized questions
3. Highlight priority levels (HIGH/MEDIUM/LOW)

**Key Points:**
- Automated gap detection
- Priority-based ranking
- Actionable questions

### Part 6: Intake Review (3 minutes)

**Script:**
"The intake draft agent synthesizes all extracted facts into a human-readable document. The review agent validates it and flags any issues. This is where human expertise comes in."

**Actions:**
1. Navigate to Intake Review page
2. Show intake document
3. Point out validation flags
4. Demonstrate approval workflow

**Key Points:**
- Human-in-the-loop review
- Validation flags
- Inline commenting
- Approval/rejection workflow

### Part 7: Migration Plan (2 minutes)

**Script:**
"Finally, the migration planning agent generates a comprehensive migration strategy with cloud recommendations, phased approach, and risk mitigation."

**Actions:**
1. Navigate to Migration Plan page
2. Show:
   - Selected strategy (Replatform)
   - Phased timeline
   - Cloud service recommendations
   - Rollback strategy

**Key Points:**
- Hybrid approach (template + LLM)
- Specific cloud recommendations
- Risk mitigation included
- Export to PDF

## Q&A Preparation

### Expected Questions:

**Q: How accurate is the fact extraction?**
A: Accuracy depends on source quality. We use confidence scoring and evidence mapping. Low-confidence facts are flagged for human review.

**Q: Can it work with sources other than Confluence?**
A: Yes, the MCP connector is plug-and-play. We can add connectors for SharePoint, Jira, GitHub, etc.

**Q: How long does the process take?**
A: Context retrieval: 2-5 minutes. Extraction: 3-7 minutes. Planning: 2-4 minutes. Total: ~15 minutes for a typical application.

**Q: What LLM providers are supported?**
A: Currently OpenAI (primary) and Gemini (fallback). The provider abstraction allows adding others.

**Q: How is state managed?**
A: We use transactional state management with optimistic locking, write-ahead logging, and checkpointing. All state changes are traced in LangSmith.

**Q: Can the system handle large applications?**
A: Yes, but processing time increases. We use chunking for large documents and caching to optimize costs.

## Troubleshooting

### Issue: Services not starting
**Solution:** Check Docker logs, verify ports not in use

### Issue: LLM API errors
**Solution:** Verify API keys in .env, check rate limits

### Issue: No context retrieved
**Solution:** Verify MCP credentials, check Confluence permissions

### Issue: Frontend not loading
**Solution:** Check backend health endpoint, verify CORS settings
```

### 6. Deployment Guide

```markdown
# Deployment Guide

## Prerequisites

- Docker 24.0+
- Podman 4.0+ (alternative to Docker)
- 8GB RAM minimum
- 20GB disk space

## Environment Setup

1. Clone repository:
   ```bash
   git clone https://github.ibm.com/poc-org-bob/migration-agent-orchestartion.git
   cd migration-agent-orchestartion
   ```

2. Create `.env` file:
   ```bash
   cp .env.example .env
   ```

3. Configure environment variables:
   ```bash
   # LLM Providers
   OPENAI_API_KEY=your_openai_key
   GEMINI_API_KEY=your_gemini_key
   
   # MCP Connector
   MCP_BASE_URL=https://your-domain.atlassian.net
   MCP_BEARER_TOKEN=your_confluence_token
   
   # LangSmith
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your_langsmith_key
   LANGCHAIN_PROJECT=migration-copilot-poc
   
   # Database
   POSTGRES_PASSWORD=secure_password
   REDIS_PASSWORD=secure_password
   ```

## Deployment with Docker Compose

```bash
# Build and start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Deployment with Podman

```bash
# Build images
podman-compose build

# Start services
podman-compose up -d

# Check status
podman ps

# View logs
podman logs -f migration-copilot-backend
```

## Health Checks

- Backend: http://localhost:8000/health
- Frontend: http://localhost:3000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001

## Monitoring

Access Grafana dashboard:
1. Navigate to http://localhost:3001
2. Login: admin / admin
3. View "Migration Copilot" dashboard

## Troubleshooting

See [Troubleshooting Guide](./troubleshooting.md)
```

## Testing Checklist

### Integration Tests
- [ ] Complete workflow execution
- [ ] State management transactions
- [ ] Error handling and recovery
- [ ] Human review workflow
- [ ] API endpoints
- [ ] MCP connector integration

### Performance Tests
- [ ] Load testing (100 concurrent users)
- [ ] Response time < 2s for API calls
- [ ] LLM call optimization
- [ ] Caching effectiveness
- [ ] Resource utilization

### UI Tests
- [ ] All pages render correctly
- [ ] Navigation works
- [ ] Forms submit properly
- [ ] Error messages display
- [ ] Responsive design
- [ ] Accessibility (WCAG 2.1 AA)

### Demo Preparation
- [ ] Demo data loaded
- [ ] Demo script tested
- [ ] All services running
- [ ] Backup plan ready
- [ ] Q&A preparation complete

## Success Criteria

- ✅ All integration tests passing
- ✅ Performance benchmarks met
- ✅ Demo runs smoothly end-to-end
- ✅ Documentation complete
- ✅ Deployment guide validated
- ✅ Troubleshooting guide ready
- ✅ System ready for stakeholder demo

## Next Steps

After successful demo:
1. Gather stakeholder feedback
2. Prioritize production features
3. Plan Phase 9: Production Hardening
4. Schedule production deployment