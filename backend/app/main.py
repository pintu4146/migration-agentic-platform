"""
FastAPI Main Application

Entry point for the Migration Copilot API.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .config import settings
from .logging_config import setup_logging
from .tracing.langsmith import setup_langsmith
from .providers.factory import ProviderFactory
from .api import mcp_router
from .models.schemas import (
    HealthResponse,
    ProviderHealthResponse,
    ProviderStatus,
    ErrorResponse,
    ProviderHealthStatus,
)

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global provider factory instance
provider_factory: ProviderFactory | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Migration Copilot API")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Primary Provider: {settings.primary_provider}")
    logger.info(f"Fallback Provider: {settings.fallback_provider}")
    
    # Setup LangSmith tracing
    setup_langsmith()
    
    # Initialize provider factory
    global provider_factory
    provider_factory = ProviderFactory()
    logger.info("Provider factory initialized")
    
    # Perform initial health check
    try:
        primary_health = await provider_factory.primary_provider.health_check()
        logger.info(f"Primary provider health: {primary_health}")
        
        if provider_factory.fallback_provider:
            fallback_health = await provider_factory.fallback_provider.health_check()
            logger.info(f"Fallback provider health: {fallback_health}")
    except Exception as e:
        logger.error(f"Provider health check failed: {str(e)}")
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Migration Copilot API")
    provider_factory = None
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Migration Copilot API",
    description="Enterprise Application Modernization Copilot - Agent Orchestration Layer",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(mcp_router)


# ============================================================================
# Exception Handlers
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors"""
    logger.warning(f"Validation error: {exc.errors()}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="Validation error",
            detail=str(exc.errors())
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc) if settings.environment != "production" else None
        ).model_dump()
    )


# ============================================================================
# Health Check Endpoints
# ============================================================================

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="API health check"
)
async def health_check() -> HealthResponse:
    """
    Check if the API is running.
    
    Returns basic health status and version information.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )


@app.get(
    "/health/providers",
    response_model=ProviderHealthResponse,
    tags=["Health"],
    summary="Provider health check"
)
async def provider_health_check() -> ProviderHealthResponse:
    """
    Check health status of LLM providers.
    
    Returns status of primary and fallback providers,
    and indicates which provider is currently active.
    """
    if provider_factory is None:
        raise RuntimeError("Provider factory not initialized")
    
    # Check primary provider
    try:
        primary_healthy = await provider_factory.primary_provider.health_check()
        primary_status = ProviderStatus(
            provider=settings.primary_provider,  # type: ignore
            status=ProviderHealthStatus.HEALTHY if primary_healthy else ProviderHealthStatus.UNHEALTHY,
            model=getattr(provider_factory.primary_provider, 'model_name', None),
            last_check=None
        )
    except Exception as e:
        logger.error(f"Primary provider health check failed: {str(e)}")
        primary_status = ProviderStatus(
            provider=settings.primary_provider,  # type: ignore
            status=ProviderHealthStatus.UNHEALTHY,
            error=str(e)
        )
    
    # Check fallback provider if configured
    fallback_status = None
    if provider_factory.fallback_provider:
        try:
            fallback_healthy = await provider_factory.fallback_provider.health_check()
            fallback_status = ProviderStatus(
                provider=settings.fallback_provider,  # type: ignore
                status=ProviderHealthStatus.HEALTHY if fallback_healthy else ProviderHealthStatus.UNHEALTHY,
                model=getattr(provider_factory.fallback_provider, 'model_name', None),
                last_check=None
            )
        except Exception as e:
            logger.error(f"Fallback provider health check failed: {str(e)}")
            fallback_status = ProviderStatus(
                provider=settings.fallback_provider,  # type: ignore
                status=ProviderHealthStatus.UNHEALTHY,
                error=str(e)
            )
    
    # Determine active provider
    active_provider = (
        settings.primary_provider  # type: ignore
        if primary_status.status == ProviderHealthStatus.HEALTHY
        else settings.fallback_provider  # type: ignore
    )
    
    return ProviderHealthResponse(
        primary=primary_status,
        fallback=fallback_status,
        active_provider=active_provider  # type: ignore
    )


@app.get(
    "/",
    tags=["Root"],
    summary="API root"
)
async def root() -> dict:
    """
    API root endpoint.
    
    Returns basic API information and available endpoints.
    """
    return {
        "name": "Migration Copilot API",
        "version": "1.0.0",
        "description": "Enterprise Application Modernization Copilot",
        "docs": "/docs" if settings.environment != "production" else None,
        "health": "/health",
        "provider_health": "/health/providers"
    }


# ============================================================================
# API Routes (Placeholder for future implementation)
# ============================================================================

# Project management routes will be added in Phase 3
# @app.post("/projects", response_model=ProjectResponse)
# async def create_project(request: ProjectCreateRequest) -> ProjectResponse:
#     ...

# @app.get("/projects/{project_id}", response_model=ProjectResponse)
# async def get_project(project_id: str) -> ProjectResponse:
#     ...

# @app.get("/projects/{project_id}/state", response_model=StateResponse)
# async def get_project_state(project_id: str) -> StateResponse:
#     ...

# Agent execution routes will be added in Phase 4
# @app.post("/projects/{project_id}/execute", response_model=AgentExecutionResponse)
# async def execute_agent(project_id: str, request: AgentExecutionRequest) -> AgentExecutionResponse:
#     ...

# MCP retrieval routes will be added in Phase 2
# @app.post("/mcp/retrieve", response_model=MCPRetrievalResponse)
# async def retrieve_context(request: MCPRetrievalRequest) -> MCPRetrievalResponse:
#     ...


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )

# Made with Bob
