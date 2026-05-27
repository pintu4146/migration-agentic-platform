# Quick Start Guide - End-to-End Testing

## Overview

This guide will help you quickly set up and test the complete Migration Copilot system with document upload and workflow orchestration.

## Prerequisites

### Required Software
- Python 3.10+
- Node.js 18+
- Podman or Docker
- Git

### Required API Keys
- OpenAI API key (for LLM operations)
- Google Gemini API key (optional, for fallback)
- IBM Context Studio MCP credentials (optional, for MCP integration)

## Step 1: Start Backend Services

### 1.1 Start Redis and Qdrant Containers

```bash
cd backend
podman-compose up -d
```

Verify containers are running:
```bash
podman ps
```

You should see:
- `redis` on port 6379
- `qdrant` on port 6333

### 1.2 Configure Environment Variables

Edit `backend/.env`:
```bash
# Required
OPENAI_API_KEY=your_openai_key_here
GEMINI_API_KEY=your_gemini_key_here

# Optional (for MCP integration)
MCP_GATEWAY_URL=https://servicesessentials.ibm.com/mcp-gateway/service/gateway/servers/YOUR_SERVER_ID/mcp
MCP_GATEWAY_TOKEN=your_bearer_token
MCP_API_KEY=your_context_studio_api_key

# Storage
REDIS_HOST=localhost
REDIS_PORT=6379
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

### 1.3 Start FastAPI Backend

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Verify backend is running:
- Open http://localhost:8000/docs
- You should see the Swagger UI

## Step 2: Start Frontend

### 2.1 Install Dependencies

```bash
cd frontend
npm install
```

This will install:
- React and React DOM
- IBM Carbon Design System
- React Router
- Axios
- Vite and build tools

### 2.2 Start Development Server

```bash
npm run dev
```

The frontend will start on http://localhost:3000

## Step 3: Test Document Upload

### 3.1 Create Test Files

Create a test directory with sample files:

**test-files/app-config.properties**
```properties
app.name=MyLegacyApp
app.version=2.5.0
server.port=8080
server.host=0.0.0.0
database.url=jdbc:postgresql://localhost:5432/mydb
database.username=admin
database.pool.size=20
cache.enabled=true
cache.ttl=3600
```

**test-files/README.md**
```markdown
# Legacy Application

## Overview
Java Spring Boot application with PostgreSQL database.

## Tech Stack
- Java 11
- Spring Boot 2.7.5
- PostgreSQL 13
- Maven 3.8
- Tomcat 9

## Architecture
Monolithic application with REST API.

## Dependencies
- Spring Web
- Spring Data JPA
- PostgreSQL Driver
- Lombok
- Jackson
```

**test-files/pom.xml**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>legacy-app</artifactId>
    <version>2.5.0</version>
    <packaging>jar</packaging>
    
    <properties>
        <java.version>11</java.version>
        <spring.boot.version>2.7.5</spring.boot.version>
    </properties>
    
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
            <version>${spring.boot.version}</version>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
            <version>${spring.boot.version}</version>
        </dependency>
        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>postgresql</artifactId>
            <version>42.5.0</version>
        </dependency>
    </dependencies>
</project>
```

### 3.2 Upload Files via UI

1. Open http://localhost:3000
2. Click "Upload Documents" or navigate to http://localhost:3000/upload
3. Enter Project ID: `test-project`
4. Click "Choose files" and select all test files
5. Click "Upload Files"

### 3.3 Verify Upload Results

You should see:
- ✓ Success indicators for each file
- Document IDs (e.g., `doc_abc123`)
- Parser used (e.g., `PropertiesParser`, `MarkdownParser`, `XMLParser`)
- Number of chunks created (e.g., 3-5 chunks per file)
- Storage location: `qdrant`

### 3.4 Verify in Backend

Check backend logs for:
```
INFO - Uploaded file: app-config.properties
INFO - Parser selected: PropertiesParser
INFO - Created 4 chunks
INFO - Stored in Qdrant collection: migration_docs
```

## Step 4: Test Workflow Execution

### 4.1 Start Workflow

1. Navigate to http://localhost:3000/workflow/test-project
2. Click "Start Workflow"
3. Verify initial state shows:
   - Phase: `init`
   - Version: `v1`
   - Project ID: `test-project`

### 4.2 Execute Workflow Steps

Click "Execute Next Step" multiple times to advance through phases:

1. **Context Retrieval** (Phase 1)
   - Fetches uploaded documents from Qdrant
   - Falls back to uploaded files if MCP unavailable
   - Creates context pack

2. **Extraction** (Phase 2)
   - Extracts facts from documents
   - Categories: technical_stack, dependencies, runtime_config, etc.
   - Assigns confidence scores

3. **Questionnaire** (Phase 3)
   - Identifies missing information
   - Generates prioritized questions
   - Maps questions to evidence gaps

### 4.3 Monitor Progress

Watch the progress indicator advance through:
- ✓ Initialize
- ✓ Context Retrieval
- ✓ Extraction
- ✓ Questionnaire
- → Intake Draft (placeholder)
- → Human Review (placeholder)
- → Migration Plan (placeholder)
- → Validation (placeholder)
- → Complete

### 4.4 View State Details

Expand accordions to see:
- **Workflow State Details**: Full JSON state
- **Context Pack**: Retrieved documents
- **Extracted Facts**: Structured fact objects
- **Questionnaire Gaps**: Generated questions

## Step 5: View Extracted Facts

### 5.1 Navigate to Facts Viewer

1. Click "View Extracted Facts" or navigate to http://localhost:3000/facts/test-project
2. Browse tabs for different categories

### 5.2 Verify Extracted Data

Check each tab:

**Technical Stack:**
- Java version: 11
- Spring Boot: 2.7.5
- Database: PostgreSQL 13

**Dependencies:**
- Spring Web
- Spring Data JPA
- PostgreSQL Driver

**Runtime Config:**
- Server port: 8080
- Database URL
- Connection pool size: 20

**Deployment:**
- Packaging: JAR
- Server: Tomcat 9

## Step 6: Verify Backend Storage

### 6.1 Check Redis State

```bash
# Connect to Redis
podman exec -it redis redis-cli

# Check workflow state
GET workflow:test-project:state

# List all keys
KEYS workflow:*
```

### 6.2 Check Qdrant Vectors

Open http://localhost:6333/dashboard

Or use API:
```bash
curl http://localhost:6333/collections/migration_docs
```

## Troubleshooting

### Backend Issues

**Problem:** Backend won't start
```bash
# Check if port 8000 is in use
netstat -ano | findstr :8000

# Check Python environment
python --version
pip list | grep fastapi
```

**Problem:** Redis connection failed
```bash
# Check Redis container
podman ps | grep redis
podman logs redis

# Test connection
redis-cli ping
```

**Problem:** Qdrant connection failed
```bash
# Check Qdrant container
podman ps | grep qdrant
podman logs qdrant

# Test connection
curl http://localhost:6333/collections
```

### Frontend Issues

**Problem:** Frontend won't start
```bash
# Check Node version
node --version

# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Problem:** API calls fail
- Check browser console for errors
- Verify backend is running on port 8000
- Check Vite proxy configuration in `vite.config.js`

**Problem:** Upload fails
- Check file size (max 50MB)
- Verify file format is supported
- Check backend logs for parser errors

### Workflow Issues

**Problem:** Workflow execution fails
- Check OpenAI API key is valid
- Verify Redis is running
- Check backend logs for agent errors
- Ensure Qdrant has documents

**Problem:** No facts extracted
- Verify documents were uploaded successfully
- Check if documents have parseable content
- Review extraction agent logs

## Expected Results

### Successful Upload
```json
{
  "document_id": "doc_abc123",
  "filename": "app-config.properties",
  "parser_used": "PropertiesParser",
  "chunks_created": 4,
  "stored_in": "qdrant",
  "project_id": "test-project"
}
```

### Successful Workflow State
```json
{
  "project_id": "test-project",
  "state_version": 3,
  "phase": "questionnaire",
  "extracted_facts": {
    "technical_stack": [...],
    "dependencies": [...],
    "runtime_config": [...]
  },
  "missing_questions": [...]
}
```

## Performance Benchmarks

### Upload Performance
- Small file (< 1MB): 1-2 seconds
- Medium file (1-10MB): 3-5 seconds
- Large file (10-50MB): 10-30 seconds

### Workflow Execution
- Context Retrieval: 2-5 seconds
- Extraction: 10-20 seconds (depends on LLM)
- Questionnaire: 5-10 seconds

### Total End-to-End
- Upload 3 files: ~5 seconds
- Execute workflow: ~30-40 seconds
- View results: Instant

## Next Steps

After successful testing:

1. **Test with Real Documents:**
   - Upload actual application documentation
   - Test with larger files
   - Verify parser accuracy

2. **Test MCP Integration:**
   - Configure MCP credentials
   - Test Confluence page retrieval
   - Verify context merging

3. **Implement Phase 5 & 6:**
   - Intake Draft Agent
   - Review/Validation Agent
   - Migration Planning Agent

4. **Prepare Demo:**
   - Create demo script
   - Record demo video
   - Prepare presentation

## Support

For issues or questions:
- Check backend logs: `backend/logs/`
- Check browser console: F12 → Console
- Review documentation: `docs/`
- Check GitHub issues

## Summary

You now have a fully functional Migration Copilot POC with:
- ✅ Document upload with 7+ parser types
- ✅ Multi-source knowledge ingestion
- ✅ LangGraph workflow orchestration
- ✅ 3 AI agents (Context, Extraction, Questionnaire)
- ✅ IBM Carbon UI
- ✅ Redis state management
- ✅ Qdrant vector storage
- ✅ End-to-end traceability

**Status:** Ready for demonstration and further development!