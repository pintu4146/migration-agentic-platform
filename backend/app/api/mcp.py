"""
MCP API Routes

Endpoints for MCP Gateway interaction and context retrieval.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse

from ..mcp.connector import MCPConnector
from ..mcp.profiles import RetrievalProfile, ProfileType, get_profile, PREDEFINED_PROFILES
from ..mcp.models import ContextPack, MCPError
from ..models.schemas import (
    MCPRetrievalRequest,
    MCPRetrievalResponse,
    MCPHealthResponse,
    ErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP"])

# Global MCP connector instance
_mcp_connector: MCPConnector | None = None


async def get_mcp_connector() -> MCPConnector:
    """Dependency to get MCP connector instance"""
    global _mcp_connector
    
    if _mcp_connector is None:
        try:
            _mcp_connector = MCPConnector()
        except Exception as e:
            logger.error(f"Failed to initialize MCP connector: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"MCP connector unavailable: {str(e)}"
            )
    
    return _mcp_connector


@router.get(
    "/health",
    response_model=MCPHealthResponse,
    summary="Check MCP Gateway health",
    responses={
        200: {"description": "MCP Gateway is healthy"},
        503: {"description": "MCP Gateway is unavailable", "model": ErrorResponse}
    }
)
async def check_mcp_health(
    connector: MCPConnector = Depends(get_mcp_connector)
) -> MCPHealthResponse:
    """
    Check MCP Gateway health status.
    
    Returns connection status and last check time.
    """
    try:
        is_healthy = await connector.health_check()
        
        return MCPHealthResponse(
            gateway_url=connector.gateway_url,
            status="healthy" if is_healthy else "unhealthy",
            last_check=datetime.utcnow(),
            error=None if is_healthy else "Health check failed"
        )
    except Exception as e:
        logger.error(f"MCP health check failed: {str(e)}")
        return MCPHealthResponse(
            gateway_url=connector.gateway_url,
            status="error",
            last_check=datetime.utcnow(),
            error=str(e)
        )


@router.post(
    "/retrieve",
    response_model=MCPRetrievalResponse,
    summary="Retrieve context using profile",
    responses={
        200: {"description": "Context retrieved successfully"},
        400: {"description": "Invalid request", "model": ErrorResponse},
        503: {"description": "MCP Gateway unavailable", "model": ErrorResponse}
    }
)
async def retrieve_context(
    request: MCPRetrievalRequest,
    connector: MCPConnector = Depends(get_mcp_connector)
) -> MCPRetrievalResponse:
    """
    Retrieve context from MCP Gateway using a retrieval profile.
    
    The profile defines what content to retrieve and how to filter it.
    """
    try:
        logger.info(f"Retrieving context for project {request.project_id}")
        
        # Convert profile dict to RetrievalProfile
        profile = RetrievalProfile(**request.profile.model_dump())
        
        # Retrieve context
        context_pack = await connector.retrieve(
            profile=profile,
            project_id=request.project_id
        )
        
        # Convert to response format
        return MCPRetrievalResponse(
            project_id=context_pack.project_id,
            profile_name=context_pack.profile_name,
            documents=[doc.model_dump() for doc in context_pack.documents],
            total_count=context_pack.total_count,
            retrieved_at=context_pack.retrieved_at
        )
        
    except MCPError as e:
        logger.error(f"MCP retrieval failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"MCP retrieval failed: {e.message}"
        )
    except ValueError as e:
        logger.error(f"Invalid profile: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid profile: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during retrieval: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Retrieval failed: {str(e)}"
        )


@router.get(
    "/profiles",
    response_model=List[Dict[str, Any]],
    summary="List available retrieval profiles",
    responses={
        200: {"description": "List of available profiles"}
    }
)
async def list_profiles() -> List[Dict[str, Any]]:
    """
    List all predefined retrieval profiles.
    
    Returns profile configurations for each agent type.
    """
    profiles = []
    
    for profile_type, profile in PREDEFINED_PROFILES.items():
        profiles.append({
            "profile_type": profile_type,
            "profile_name": profile.profile_name,
            "description": f"Profile for {profile_type.value} agent",
            "source_types": profile.source_types,
            "max_results": profile.max_results,
            "include_attachments": profile.include_attachments,
            "include_comments": profile.include_comments
        })
    
    return profiles


@router.get(
    "/profiles/{profile_type}",
    response_model=Dict[str, Any],
    summary="Get specific profile configuration",
    responses={
        200: {"description": "Profile configuration"},
        404: {"description": "Profile not found", "model": ErrorResponse}
    }
)
async def get_profile_config(profile_type: str) -> Dict[str, Any]:
    """
    Get configuration for a specific profile type.
    
    Returns detailed profile configuration including all filters and options.
    """
    try:
        # Convert string to ProfileType enum
        profile_enum = ProfileType(profile_type.lower())
        profile = get_profile(profile_enum)
        
        return profile.model_dump()
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile type '{profile_type}' not found"
        )


@router.post(
    "/profiles/validate",
    response_model=Dict[str, Any],
    summary="Validate a custom profile",
    responses={
        200: {"description": "Profile is valid"},
        400: {"description": "Profile is invalid", "model": ErrorResponse}
    }
)
async def validate_profile(profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a custom retrieval profile configuration.
    
    Checks if the profile configuration is valid before using it.
    """
    try:
        # Try to create profile from data
        profile = RetrievalProfile(**profile_data)
        
        return {
            "valid": True,
            "profile_name": profile.profile_name,
            "message": "Profile configuration is valid"
        }
        
    except Exception as e:
        logger.warning(f"Profile validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid profile configuration: {str(e)}"
        )


@router.on_event("shutdown")
async def shutdown_mcp_connector():
    """Cleanup MCP connector on shutdown"""
    global _mcp_connector
    
    if _mcp_connector:
        await _mcp_connector.close()
        _mcp_connector = None
        logger.info("MCP connector closed")

# Made with Bob
