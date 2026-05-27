"""
Orchestration API Endpoints

REST API for workflow orchestration and state management.
Follows SOLID principles with clear separation of concerns.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Body
from pydantic import BaseModel, Field

from ..orchestration.workflow import WorkflowOrchestrator, get_workflow_orchestrator
from ..orchestration.state import WorkflowPhase, MigrationState
from ..orchestration.state_manager import StateManager, get_state_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orchestration", tags=["orchestration"])


# Request/Response Models

class StartWorkflowRequest(BaseModel):
    """Request to start a new workflow"""
    project_id: str = Field(description="Unique project identifier")
    mcp_profile: str = Field(
        default="context_retrieval_profile",
        description="MCP retrieval profile name"
    )
    query: Optional[str] = Field(
        default=None,
        description="Optional search query"
    )


class StartWorkflowResponse(BaseModel):
    """Response for workflow start"""
    project_id: str
    state_version: int
    phase: str
    message: str


class ExecuteWorkflowRequest(BaseModel):
    """Request to execute workflow"""
    project_id: str = Field(description="Project identifier")


class ExecuteWorkflowResponse(BaseModel):
    """Response for workflow execution"""
    project_id: str
    state_version: int
    phase: str
    completed: bool
    message: str


class ResumeWorkflowRequest(BaseModel):
    """Request to resume paused workflow"""
    project_id: str = Field(description="Project identifier")
    updates: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional state updates (e.g., human review approval)"
    )


class ResumeWorkflowResponse(BaseModel):
    """Response for workflow resume"""
    project_id: str
    state_version: int
    phase: str
    message: str


class GetStateResponse(BaseModel):
    """Response for get state"""
    project_id: str
    state_version: int
    phase: str
    created_at: str
    updated_at: str
    context_pack: Optional[Dict[str, Any]]
    extracted_facts: Optional[Dict[str, Any]]
    missing_questions: list
    intake_draft: Optional[Dict[str, Any]]
    human_reviewed: bool
    migration_plan: Optional[Dict[str, Any]]
    validation_results: Optional[Dict[str, Any]]


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    timestamp: str
    orchestrator_ready: bool
    state_manager_ready: bool


# API Endpoints

@router.post("/start", response_model=StartWorkflowResponse)
async def start_workflow(
    request: StartWorkflowRequest
) -> StartWorkflowResponse:
    """
    Start a new workflow.
    
    Creates initial state and prepares for execution.
    
    Args:
        request: Workflow start request
        
    Returns:
        StartWorkflowResponse with initial state info
        
    Raises:
        HTTPException: If workflow start fails
    """
    try:
        orchestrator = get_workflow_orchestrator()
        
        initial_state = await orchestrator.start_workflow(
            project_id=request.project_id,
            mcp_profile=request.mcp_profile,
            query=request.query
        )
        
        return StartWorkflowResponse(
            project_id=initial_state["project_id"],
            state_version=initial_state["state_version"],
            phase=initial_state["phase"],
            message=f"Workflow started for project {request.project_id}"
        )
        
    except Exception as e:
        logger.error(f"Failed to start workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow: {str(e)}"
        )


@router.post("/execute", response_model=ExecuteWorkflowResponse)
async def execute_workflow(
    request: ExecuteWorkflowRequest
) -> ExecuteWorkflowResponse:
    """
    Execute workflow for a project.
    
    Runs the workflow until completion or pause point.
    
    Args:
        request: Workflow execution request
        
    Returns:
        ExecuteWorkflowResponse with final state info
        
    Raises:
        HTTPException: If workflow execution fails
    """
    try:
        orchestrator = get_workflow_orchestrator()
        
        final_state = await orchestrator.execute_workflow(
            project_id=request.project_id
        )
        
        completed = final_state["phase"] == WorkflowPhase.COMPLETE.value
        
        return ExecuteWorkflowResponse(
            project_id=final_state["project_id"],
            state_version=final_state["state_version"],
            phase=final_state["phase"],
            completed=completed,
            message=f"Workflow {'completed' if completed else 'paused'} at phase {final_state['phase']}"
        )
        
    except Exception as e:
        logger.error(f"Failed to execute workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute workflow: {str(e)}"
        )


@router.post("/resume", response_model=ResumeWorkflowResponse)
async def resume_workflow(
    request: ResumeWorkflowRequest
) -> ResumeWorkflowResponse:
    """
    Resume a paused workflow.
    
    Optionally applies state updates (e.g., human review approval).
    
    Args:
        request: Workflow resume request
        
    Returns:
        ResumeWorkflowResponse with updated state info
        
    Raises:
        HTTPException: If workflow resume fails
    """
    try:
        orchestrator = get_workflow_orchestrator()
        
        updated_state = await orchestrator.resume_workflow(
            project_id=request.project_id,
            updates=request.updates
        )
        
        return ResumeWorkflowResponse(
            project_id=updated_state["project_id"],
            state_version=updated_state["state_version"],
            phase=updated_state["phase"],
            message=f"Workflow resumed for project {request.project_id}"
        )
        
    except Exception as e:
        logger.error(f"Failed to resume workflow: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume workflow: {str(e)}"
        )


@router.get("/state/{project_id}", response_model=GetStateResponse)
async def get_state(project_id: str) -> GetStateResponse:
    """
    Get current workflow state.
    
    Args:
        project_id: Project identifier
        
    Returns:
        GetStateResponse with current state
        
    Raises:
        HTTPException: If state not found or retrieval fails
    """
    try:
        state_manager = await get_state_manager()
        state = await state_manager.get_state(project_id)
        
        if state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"State not found for project {project_id}"
            )
        
        return GetStateResponse(
            project_id=state["project_id"],
            state_version=state["state_version"],
            phase=state["phase"],
            created_at=state["created_at"],
            updated_at=state["updated_at"],
            context_pack=state.get("context_pack"),
            extracted_facts=state.get("extracted_facts"),
            missing_questions=state.get("missing_questions", []),
            intake_draft=state.get("intake_draft"),
            human_reviewed=state.get("human_reviewed", False),
            migration_plan=state.get("migration_plan"),
            validation_results=state.get("validation_results")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get state: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get state: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.
    
    Returns:
        HealthResponse with service status
    """
    try:
        orchestrator = get_workflow_orchestrator()
        state_manager = await get_state_manager()
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow().isoformat(),
            orchestrator_ready=orchestrator is not None,
            state_manager_ready=state_manager is not None
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow().isoformat(),
            orchestrator_ready=False,
            state_manager_ready=False
        )


# Made with Bob