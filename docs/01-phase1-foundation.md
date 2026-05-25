# Phase 1: Project Foundation & Infrastructure Setup

## Overview

Phase 1 establishes the foundational infrastructure for the migration copilot POC. This includes project structure, FastAPI backend, provider abstraction, LangSmith integration, and containerization with Podman.

## Objectives

1. Create project structure and skeleton
2. Set up FastAPI backend with health checks
3. Implement LLM provider abstraction layer
4. Configure LangSmith tracing
5. Set up Podman containerization
6. Implement configuration management
7. Add structured logging
8. Create development environment

## Deliverables

### 1. Project Structure

```
mig-26/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI entry point
│   │   ├── config.py                  # Configuration management
│   │   ├── logging_config.py          # Structured logging
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # Abstract provider interface
│   │   │   ├── openai_provider.py     # OpenAI implementation
│   │   │   ├── gemini_provider.py     # Gemini implementation
│   │   │   └── factory.py             # Provider factory with fallback
│   │   ├── tracing/
│   │   │   ├── __init__.py
│   │   │   └── langsmith.py           # LangSmith integration
│   │   └── models/
│   │       ├── __init__.py
│   │       └── schemas.py             # Pydantic models
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_providers.py
│   │   └── test_config.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   ├── .env.example
│   └── pytest.ini
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── index.tsx
│   │   └── components/
│   ├── package.json
│   ├── tsconfig.json
│   ├── Dockerfile
│   └── .env.example
├── docs/
│   ├── 00-architecture-overview.md
│   ├── 01-phase1-foundation.md
│   └── ...
├── docker-compose.yml
├── podman-compose.yml
├── .gitignore
├── .env.example
└── README.md
```

### 2. Provider Abstraction Layer

#### Base Provider Interface

```python
# backend/app/providers/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class ProviderResponse(BaseModel):
    """Standardized response from any LLM provider"""
    content: str
    model: str
    usage: Dict[str, int]
    metadata: Dict[str, Any]
    provider: str

class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
    
    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> ProviderResponse:
        """Generate text completion"""
        pass
    
    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate structured output matching schema"""
        pass
    
    @abstractmethod
    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> ProviderResponse:
        """Generate with tool/function calling"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available"""
        pass
```

#### OpenAI Provider Implementation

```python
# backend/app/providers/openai_provider.py
from openai import AsyncOpenAI
from typing import Dict, Any, List, Optional
import json

class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation"""
    
    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        super().__init__(api_key, model)
        self.client = AsyncOpenAI(api_key=api_key)
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> ProviderResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        return ProviderResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            metadata={"finish_reason": response.choices[0].finish_reason},
            provider="openai"
        )
    
    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({
            "role": "user",
            "content": f"{prompt}\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
        })
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        return json.loads(response.choices[0].message.content)
    
    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> ProviderResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        return ProviderResponse(
            content=response.choices[0].message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            },
            metadata={
                "finish_reason": response.choices[0].finish_reason,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "function": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                    for tc in (response.choices[0].message.tool_calls or [])
                ]
            },
            provider="openai"
        )
    
    async def health_check(self) -> bool:
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False
```

#### Gemini Provider Implementation

```python
# backend/app/providers/gemini_provider.py
import google.generativeai as genai
from typing import Dict, Any, List, Optional
import json

class GeminiProvider(LLMProvider):
    """Google Gemini provider implementation"""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        super().__init__(api_key, model)
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model)
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> ProviderResponse:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        response = await self.client.generate_content_async(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
        )
        
        return ProviderResponse(
            content=response.text,
            model=self.model,
            usage={
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "completion_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count
            },
            metadata={"finish_reason": response.candidates[0].finish_reason.name},
            provider="gemini"
        )
    
    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        full_prompt = f"{system_prompt}\n\n" if system_prompt else ""
        full_prompt += f"{prompt}\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
        
        response = await self.client.generate_content_async(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                response_mime_type="application/json"
            )
        )
        
        return json.loads(response.text)
    
    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> ProviderResponse:
        # Convert OpenAI-style tools to Gemini format
        gemini_tools = self._convert_tools(tools)
        
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        
        response = await self.client.generate_content_async(
            full_prompt,
            tools=gemini_tools
        )
        
        return ProviderResponse(
            content=response.text,
            model=self.model,
            usage={
                "prompt_tokens": response.usage_metadata.prompt_token_count,
                "completion_tokens": response.usage_metadata.candidates_token_count,
                "total_tokens": response.usage_metadata.total_token_count
            },
            metadata={
                "finish_reason": response.candidates[0].finish_reason.name,
                "tool_calls": [
                    {
                        "function": fc.name,
                        "arguments": fc.args
                    }
                    for fc in (response.candidates[0].content.parts[0].function_call if hasattr(response.candidates[0].content.parts[0], 'function_call') else [])
                ]
            },
            provider="gemini"
        )
    
    def _convert_tools(self, tools: List[Dict[str, Any]]) -> List:
        """Convert OpenAI tool format to Gemini format"""
        # Implementation details for tool conversion
        pass
    
    async def health_check(self) -> bool:
        try:
            response = await self.client.generate_content_async("test")
            return True
        except Exception:
            return False
```

#### Provider Factory with Circuit Breaker

```python
# backend/app/providers/factory.py
from typing import Optional
from datetime import datetime, timedelta
from .base import LLMProvider
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider
from ..config import Settings
import logging

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Circuit breaker for provider fallback"""
    
    def __init__(self, threshold: int = 3, timeout: timedelta = timedelta(minutes=5)):
        self.threshold = threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure: Optional[datetime] = None
        self.is_open = False
    
    def record_failure(self):
        """Record a failure"""
        self.failures += 1
        self.last_failure = datetime.utcnow()
        
        if self.failures >= self.threshold:
            self.is_open = True
            logger.warning(f"Circuit breaker opened after {self.failures} failures")
    
    def record_success(self):
        """Record a success"""
        self.failures = 0
        self.is_open = False
    
    def should_attempt(self) -> bool:
        """Check if we should attempt to use this provider"""
        if not self.is_open:
            return True
        
        if self.last_failure:
            elapsed = datetime.utcnow() - self.last_failure
            if elapsed >= self.timeout:
                logger.info("Circuit breaker timeout elapsed, attempting reset")
                self.failures = 0
                self.is_open = False
                return True
        
        return False

class ProviderFactory:
    """Factory for creating and managing LLM providers with fallback"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.primary_provider = self._create_provider(
            settings.PRIMARY_PROVIDER,
            settings.OPENAI_API_KEY if settings.PRIMARY_PROVIDER == "openai" else settings.GEMINI_API_KEY
        )
        self.fallback_provider = self._create_provider(
            settings.FALLBACK_PROVIDER,
            settings.GEMINI_API_KEY if settings.FALLBACK_PROVIDER == "gemini" else settings.OPENAI_API_KEY
        )
        self.circuit_breaker = CircuitBreaker()
    
    def _create_provider(self, provider_type: str, api_key: str) -> LLMProvider:
        """Create provider instance"""
        if provider_type == "openai":
            return OpenAIProvider(api_key=api_key)
        elif provider_type == "gemini":
            return GeminiProvider(api_key=api_key)
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
    
    async def get_provider(self) -> LLMProvider:
        """Get provider with automatic fallback"""
        if self.circuit_breaker.should_attempt():
            try:
                # Test primary provider health
                if await self.primary_provider.health_check():
                    self.circuit_breaker.record_success()
                    logger.info(f"Using primary provider: {self.settings.PRIMARY_PROVIDER}")
                    return self.primary_provider
                else:
                    self.circuit_breaker.record_failure()
            except Exception as e:
                logger.error(f"Primary provider failed: {e}")
                self.circuit_breaker.record_failure()
        
        # Use fallback
        logger.warning(f"Falling back to: {self.settings.FALLBACK_PROVIDER}")
        return self.fallback_provider
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all providers"""
        return {
            "primary": await self.primary_provider.health_check(),
            "fallback": await self.fallback_provider.health_check()
        }
```

### 3. Configuration Management

```python
# backend/app/config.py
from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from typing import Optional

class Settings(BaseSettings):
    """Application settings with validation"""
    
    # API Settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_TITLE: str = "Migration Copilot API"
    API_VERSION: str = "1.0.0"
    
    # LLM Provider Settings
    PRIMARY_PROVIDER: str = "openai"
    FALLBACK_PROVIDER: str = "gemini"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-pro"
    
    # MCP Settings
    MCP_BASE_URL: Optional[str] = None
    MCP_BEARER_TOKEN: Optional[str] = None
    MCP_TIMEOUT: int = 30
    MCP_RETRY_COUNT: int = 3
    
    # Confluence Settings
    CONFLUENCE_URL: Optional[str] = None
    CONFLUENCE_USERNAME: Optional[str] = None
    CONFLUENCE_API_TOKEN: Optional[str] = None
    
    # LangSmith Settings
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_PROJECT: str = "migration-copilot-poc"
    LANGSMITH_TRACING: bool = True
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    
    # Vector Store Settings
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_IN_MEMORY: bool = True
    QDRANT_COLLECTION: str = "migration_docs"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000"]
    
    @field_validator('PRIMARY_PROVIDER', 'FALLBACK_PROVIDER')
    @classmethod
    def validate_provider(cls, v: str) -> str:
        if v not in ['openai', 'gemini']:
            raise ValueError(f"Provider must be 'openai' or 'gemini', got '{v}'")
        return v
    
    @model_validator(mode='after')
    def validate_provider_keys(self):
        if self.PRIMARY_PROVIDER == 'openai' and not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY required when PRIMARY_PROVIDER is 'openai'")
        if self.PRIMARY_PROVIDER == 'gemini' and not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY required when PRIMARY_PROVIDER is 'gemini'")
        if self.FALLBACK_PROVIDER == 'openai' and not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY required when FALLBACK_PROVIDER is 'openai'")
        if self.FALLBACK_PROVIDER == 'gemini' and not self.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY required when FALLBACK_PROVIDER is 'gemini'")
        return self
    
    @model_validator(mode='after')
    def validate_mcp_config(self):
        if self.MCP_BASE_URL and not self.MCP_BEARER_TOKEN:
            raise ValueError("MCP_BEARER_TOKEN required when MCP_BASE_URL is set")
        return self
    
    @model_validator(mode='after')
    def validate_langsmith(self):
        if self.LANGSMITH_TRACING and not self.LANGSMITH_API_KEY:
            raise ValueError("LANGSMITH_API_KEY required when LANGSMITH_TRACING is enabled")
        return self
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Global settings instance
settings = Settings()
```

### 4. Structured Logging

```python
# backend/app/logging_config.py
import logging
import json
from datetime import datetime
from typing import Dict, Any
import contextvars

# Context variable for correlation ID
correlation_id = contextvars.ContextVar('correlation_id', default=None)

class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": correlation_id.get(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra'):
            log_data.update(record.extra)
        
        return json.dumps(log_data)

def setup_logging(log_level: str = "INFO", log_format: str = "json"):
    """Setup application logging"""
    
    if log_format == "json":
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        )
    
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
```

### 5. LangSmith Integration

```python
# backend/app/tracing/langsmith.py
from langsmith import Client, traceable
from typing import Dict, Any, Optional
import os
from datetime import datetime

class LangSmithTracer:
    """LangSmith tracing integration"""
    
    def __init__(self, api_key: str, project_name: str):
        self.client = Client(api_key=api_key)
        self.project_name = project_name
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = project_name
        os.environ["LANGCHAIN_API_KEY"] = api_key
    
    @traceable(name="agent_execution")
    async def trace_agent(
        self,
        agent_name: str,
        phase: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Trace agent execution"""
        return {
            "agent": agent_name,
            "phase": phase,
            "input": input_data,
            "output": output_data,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @traceable(name="state_transition")
    async def trace_state_change(
        self,
        from_phase: str,
        to_phase: str,
        state_version: int,
        state_diff: Dict[str, Any],
        committed_by: str
    ) -> Dict[str, Any]:
        """Trace state transitions"""
        return {
            "transition": f"{from_phase} -> {to_phase}",
            "version": state_version,
            "diff": state_diff,
            "committed_by": committed_by,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @traceable(name="mcp_request")
    async def trace_mcp_request(
        self,
        profile_name: str,
        request_params: Dict[str, Any],
        response_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Trace MCP requests"""
        return {
            "profile": profile_name,
            "request": request_params,
            "response": response_summary,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @traceable(name="llm_call")
    async def trace_llm_call(
        self,
        provider: str,
        model: str,
        prompt_summary: str,
        response_summary: str,
        usage: Dict[str, int]
    ) -> Dict[str, Any]:
        """Trace LLM calls"""
        return {
            "provider": provider,
            "model": model,
            "prompt": prompt_summary,
            "response": response_summary,
            "usage": usage,
            "timestamp": datetime.utcnow().isoformat()
        }
```

### 6. FastAPI Application

```python
# backend/app/main.py
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import logging

from .config import settings
from .logging_config import setup_logging, correlation_id
from .providers.factory import ProviderFactory
from .tracing.langsmith import LangSmithTracer

# Setup logging
setup_logging(settings.LOG_LEVEL, settings.LOG_FORMAT)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize provider factory
provider_factory = ProviderFactory(settings)

# Initialize LangSmith tracer
tracer = None
if settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY:
    tracer = LangSmithTracer(
        api_key=settings.LANGSMITH_API_KEY,
        project_name=settings.LANGSMITH_PROJECT
    )

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Migration Copilot API")
    logger.info(f"Primary Provider: {settings.PRIMARY_PROVIDER}")
    logger.info(f"Fallback Provider: {settings.FALLBACK_PROVIDER}")
    logger.info(f"LangSmith Tracing: {settings.LANGSMITH_TRACING}")

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.API_VERSION
    }

@app.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """Readiness check - validates dependencies"""
    checks = {
        "providers": await provider_factory.health_check(),
        "langsmith": settings.LANGSMITH_TRACING and tracer is not None
    }
    
    all_ready = all([
        any(checks["providers"].values()),  # At least one provider healthy
        checks["langsmith"] or not settings.LANGSMITH_TRACING  # LangSmith if enabled
    ])
    
    status_code = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        status_code=status_code,
        content={
            "ready": all_ready,
            "checks": checks,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
```

## Testing Phase 1

### Unit Tests

```python
# backend/tests/test_providers.py
import pytest
from app.providers.openai_provider import OpenAIProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.factory import ProviderFactory
from app.config import Settings

@pytest.mark.asyncio
async def test_openai_provider():
    provider = OpenAIProvider(api_key="test-key")
    assert provider.model == "gpt-4-turbo-preview"

@pytest.mark.asyncio
async def test_provider_factory_fallback():
    settings = Settings(
        PRIMARY_PROVIDER="openai",
        FALLBACK_PROVIDER="gemini",
        OPENAI_API_KEY="test-key-1",
        GEMINI_API_KEY="test-key-2"
    )
    factory = ProviderFactory(settings)
    provider = await factory.get_provider()
    assert provider is not None
```

### Integration Tests

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test readiness endpoint
curl http://localhost:8000/ready

# Test provider health
curl http://localhost:8000/providers/health
```

## Success Criteria

- [ ] FastAPI server starts successfully
- [ ] Health and readiness endpoints respond correctly
- [ ] Provider abstraction works with both OpenAI and Gemini
- [ ] Automatic fallback triggers on primary provider failure
- [ ] LangSmith tracing captures all operations
- [ ] Configuration validation catches invalid settings
- [ ] Structured logging outputs JSON format
- [ ] Podman containers run successfully
- [ ] All unit tests pass

## Next Steps

After Phase 1 completion, proceed to [Phase 2: MCP Connector](./02-phase2-mcp-connector.md)