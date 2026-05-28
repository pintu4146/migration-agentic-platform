"""
Orchestration API Endpoints

REST API for workflow orchestration and state management.
Follows SOLID principles with clear separation of concerns.
"""

import logging
from typing import Dict, Any, Optional
import json
import asyncio
from datetime import datetime

from fastapi.responses import StreamingResponse
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


def _get_phase_details(state: Any) -> Dict[str, Any]:
    """
    Extract phase-specific details from state for UI display.
    
    Args:
        state: Current workflow state
        
    Returns:
        Dictionary with phase-specific details
    """
    phase = state.get("phase", "init")
    details = {
        "phase": phase,
        "status": "in_progress"
    }
    
    # Add phase-specific information
    if phase == "context_retrieval":
        docs = state.get("normalized_docs", [])
        details["documents_retrieved"] = len(docs)
        details["context_source"] = state.get("context_source")
        
    elif phase == "extraction":
        facts = state.get("extracted_facts", {})
        if facts:
            total_facts = sum(len(facts.get(category, [])) for category in facts.keys())
            details["facts_extracted"] = total_facts
            details["categories"] = list(facts.keys())
        
    elif phase == "questionnaire":
        questions = state.get("missing_questions", [])
        details["questions_generated"] = len(questions)
        high_priority = sum(1 for q in questions if q.get("priority") == "HIGH")
        details["high_priority_questions"] = high_priority
        
    elif phase == "intake_draft":
        draft = state.get("intake_draft")
        details["draft_created"] = draft is not None
        
    elif phase == "human_review":
        details["status"] = "awaiting_review"
        details["reviewed"] = state.get("human_reviewed", False)
        
    elif phase == "complete":
        details["status"] = "completed"
        plan = state.get("migration_plan")
        details["plan_generated"] = plan is not None
    
    return details


@router.get("/stream/{project_id}")
async def stream_workflow_state(project_id: str):
    """
    Server-Sent Events endpoint for real-time workflow state updates.
    
    Uses LangGraph native streaming for real-time event delivery.
    Streams workflow state changes to the client as they happen.
    
    Args:
        project_id: Project identifier
        
    Returns:
        StreamingResponse with SSE events
    """
    async def event_generator():
        """Generate SSE events using LangGraph native streaming"""
        last_phase = None
        
        try:
            # Get orchestrator
            orchestrator = get_workflow_orchestrator()
            
            # Get current state from state manager
            state_manager = await get_state_manager()
            state = await state_manager.get_state(project_id)
            
            if not state:
                # Send initial connection event
                yield f"event: connected\n"
                yield f"data: {json.dumps({'project_id': project_id, 'status': 'waiting'})}\n\n"
                logger.info(f"SSE: Connected for {project_id}, waiting for state")
                
                # Poll for state initialization
                while not state:
                    await asyncio.sleep(0.5)
                    state = await state_manager.get_state(project_id)
            
            # Send initial state
            initial_event = {
                "state": state,
                "phase_info": {
                    "current_phase": state.get("phase"),
                    "version": state.get("state_version", 0),
                    "timestamp": datetime.utcnow().isoformat(),
                    "details": _get_phase_details(state)
                }
            }
            yield f"event: state_update\n"
            yield f"data: {json.dumps(initial_event)}\n\n"
            logger.info(f"SSE: Sent initial state for {project_id}")
            
            last_phase = state.get("phase")
            
            # Now poll for state changes (workflow updates state in Redis)
            while True:
                try:
                    await asyncio.sleep(0.5)
                    
                    # Get updated state
                    updated_state = await state_manager.get_state(project_id)
                    
                    if not updated_state:
                        continue
                    
                    current_phase = updated_state.get("phase")
                    current_version = updated_state.get("state_version", 0)
                    
                    # Check if state changed
                    if (current_version != state.get("state_version", 0) or
                        current_phase != last_phase):
                        
                        # Send phase transition event if phase changed
                        if current_phase != last_phase and last_phase is not None:
                            phase_event = {
                                "from_phase": last_phase,
                                "to_phase": current_phase,
                                "version": current_version,
                                "timestamp": datetime.utcnow().isoformat()
                            }
                            yield f"event: phase_transition\n"
                            yield f"data: {json.dumps(phase_event)}\n\n"
                            logger.info(f"SSE: Phase transition {last_phase} → {current_phase}")
                        
                        # Send state update event
                        event_data = {
                            "state": updated_state,
                            "phase_info": {
                                "current_phase": current_phase,
                                "version": current_version,
                                "timestamp": datetime.utcnow().isoformat(),
                                "details": _get_phase_details(updated_state)
                            }
                        }
                        yield f"event: state_update\n"
                        yield f"data: {json.dumps(event_data)}\n\n"
                        logger.info(f"SSE: Sent state update for {project_id}, version {current_version}, phase: {current_phase}")
                        
                        # Update tracking variables
                        state = updated_state
                        last_phase = current_phase
                    
                except Exception as e:
                    logger.error(f"SSE error for {project_id}: {e}")
                    error_data = json.dumps({"error": str(e)})
                    yield f"event: error\n"
                    yield f"data: {error_data}\n\n"
                    await asyncio.sleep(2)
                    
        except asyncio.CancelledError:
            logger.info(f"SSE connection closed for {project_id}")
            raise
        except Exception as e:
            logger.error(f"SSE fatal error for {project_id}: {e}", exc_info=True)
            error_data = json.dumps({"error": str(e), "fatal": True})
            yield f"event: error\n"
            yield f"data: {error_data}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

