# Migration Copilot Backend

FastAPI-based backend for the Migration Copilot POC.

## 🏗️ Architecture

### Core Components

1. **Configuration Management** (`app/config.py`)
   - Pydantic Settings for type-safe configuration
   - Environment variable loading
   - Provider validation

2. **Provider Abstraction** (`app/providers/`)
   - Abstract base class for LLM providers
   - OpenAI implementation
   - Gemini implementation
   - Factory with circuit breaker and automatic fallback

3. **LangSmith Tracing** (`app/tracing/`)
   - Comprehensive tracing for all operations
   - Decorator-based tracing
   - Context manager for code blocks
   - Manual tracing helper class

4. **API Models** (`app/models/`)
   - Pydantic schemas for request/response validation
   - Type-safe data models

5. **FastAPI Application** (`app/main.py`)
   - Health check endpoints
   - Provider status endpoints
   - CORS middleware
   - Exception handlers
   - Lifespan management

## 🚀 Quick Start

### Local Development

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
# Required: OPENAI_API_KEY or GEMINI_API_KEY
# Optional: LANGCHAIN_API_KEY for tracing

# Run tests
pytest

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker/Podman

```bash
# Build image
podman build -t migration-copilot-backend .

# Run container
podman run -d \
  --name migration-copilot-backend \
  -p 8000:8000 \
  --env-file .env \
  migration-copilot-backend
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run with markers
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m provider      # Provider-specific tests

# View coverage report
open htmlcov/index.html
```

## 📊 API Endpoints

### Health Checks

```bash
# Basic health check
GET /health

# Provider health check
GET /health/providers

# API root
GET /
```

### Future Endpoints (Phase 3+)

```bash
# Project management
POST /projects
GET /projects/{project_id}
GET /projects/{project_id}/state

# Agent execution
POST /projects/{project_id}/execute

# MCP retrieval
POST /mcp/retrieve
```

## 🔧 Configuration

### Required Environment Variables

```bash
# LLM Provider (at least one required)
PRIMARY_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Or use Gemini
PRIMARY_PROVIDER=gemini
GEMINI_API_KEY=...
```

### Optional Environment Variables

```bash
# Fallback provider
FALLBACK_PROVIDER=gemini
GEMINI_API_KEY=...

# LangSmith tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=...
LANGCHAIN_PROJECT=migration-copilot-poc

# MCP connector
MCP_BASE_URL=https://your-domain.atlassian.net/wiki
MCP_BEARER_TOKEN=...

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

See `.env.example` for complete list.

## 🏛️ Provider Abstraction

### Architecture

```python
# Abstract base class
class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> ProviderResponse:
        pass
    
    @abstractmethod
    async def generate_structured(self, prompt: str, schema: dict, **kwargs) -> ProviderResponse:
        pass
    
    @abstractmethod
    async def generate_with_tools(self, prompt: str, tools: list, **kwargs) -> ProviderResponse:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass
```

### Circuit Breaker Pattern

The provider factory implements automatic fallback:

1. Primary provider fails → Circuit opens
2. Requests route to fallback provider
3. After timeout → Circuit half-opens
4. Test request to primary → Success → Circuit closes
5. Test request fails → Circuit remains open

### Usage

```python
from app.providers.factory import ProviderFactory

# Initialize factory
factory = ProviderFactory()

# Get active provider (handles fallback automatically)
provider = factory.get_provider()

# Generate text
response = await provider.generate("Your prompt here")

# Generate structured output
response = await provider.generate_structured(
    prompt="Extract facts",
    schema={"type": "object", "properties": {...}}
)

# Generate with tools
response = await provider.generate_with_tools(
    prompt="Use tools to answer",
    tools=[{"name": "search", "description": "..."}]
)
```

## 📈 Tracing

### LangSmith Integration

```python
from app.tracing.langsmith import trace_operation, trace_context, get_tracer

# Decorator-based tracing
@trace_operation("extract_facts", run_type="chain", tags=["extraction"])
async def extract_facts(state):
    # Your code here
    pass

# Context manager tracing
with trace_context("process_documents", inputs={"doc_count": 5}):
    # Your code here
    pass

# Manual tracing
tracer = get_tracer()
await tracer.trace_llm_call(
    provider="openai",
    model="gpt-4",
    prompt="...",
    response="...",
    usage={"prompt_tokens": 10, "completion_tokens": 20}
)
```

## 🔍 Logging

Structured logging with JSON format:

```python
import logging

logger = logging.getLogger(__name__)

# Logs are automatically formatted as JSON in production
logger.info("Processing request", extra={
    "project_id": "proj_123",
    "phase": "extraction",
    "state_version": 5
})
```

## 🐛 Debugging

### View Logs

```bash
# Development server logs
uvicorn app.main:app --reload --log-level debug

# Container logs
podman logs -f migration-copilot-backend
```

### LangSmith Traces

1. Enable tracing in `.env`:
   ```bash
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your-key
   ```

2. View traces at: https://smith.langchain.com

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check provider health
curl http://localhost:8000/health/providers
```

## 📦 Dependencies

### Production

- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `pydantic` - Data validation
- `openai` - OpenAI SDK
- `google-generativeai` - Gemini SDK
- `langchain` - LangChain framework
- `langgraph` - Graph-based workflows
- `langsmith` - Tracing
- `redis` - Caching
- `qdrant-client` - Vector storage

### Development

- `pytest` - Testing framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting
- `black` - Code formatting
- `isort` - Import sorting
- `mypy` - Type checking

## 🚧 Development Roadmap

- ✅ Phase 1: Foundation (Configuration, Providers, Tracing)
- 🚧 Phase 2: MCP Connector
- 🚧 Phase 3: LangGraph Orchestration
- 🚧 Phase 4: Core Agents
- 🚧 Phase 5: Intake & Review
- 🚧 Phase 6: Migration Planning

## 📝 Code Style

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Type check
mypy app/

# Lint
flake8 app/ tests/
```

## 🤝 Contributing

1. Create feature branch
2. Write tests
3. Implement feature
4. Run tests and linting
5. Submit PR

## 📄 License

[Your License Here]