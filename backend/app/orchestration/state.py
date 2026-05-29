"""
Workflow State Schema

Defines the shared state structure for LangGraph workflow.
Follows SOLID principles with clear type definitions.
"""

from typing import TypedDict, Dict, Any, List, Optional, Annotated
from datetime import datetime
from enum import Enum
from operator import add


def merge_lists(left: List[Any], right: List[Any]) -> List[Any]:
    """Merge two lists by appending right to left."""
    return left + right


def merge_dicts(left: Optional[Dict[str, Any]], right: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Merge two dicts, with right taking precedence."""
    if right is None:
        return left
    if left is None:
        return right
    return {**left, **right}


class WorkflowPhase(str, Enum):
    """
    Workflow execution phases.
    
    Each phase represents a distinct stage in the migration workflow.
    """
    INIT = "init"
    CONTEXT_RETRIEVAL = "context_retrieval"
    EXTRACTION = "extraction"
    QUESTIONNAIRE = "questionnaire"
    INTAKE_DRAFT = "intake_draft"
    HUMAN_REVIEW = "human_review"
    MIGRATION_PLANNING = "migration_planning"
    VALIDATION = "validation"
    COMPLETE = "complete"
    ERROR = "error"


class StateChangelogEntry(TypedDict):
    """
    Single changelog entry for state audit trail.
    
    Tracks who changed what and when.
    """
    version: int
    patch: Dict[str, Any]
    committed_by: str
    committed_at: str
    previous_phase: str
    new_phase: str
    description: Optional[str]


class MigrationState(TypedDict):
    """
    Complete workflow state with version control.
    
    This is the single source of truth for the entire workflow.
    All agents read from and propose updates to this state.
    
    Design Principles:
    - Immutable: Agents cannot directly modify state
    - Versioned: Every change increments state_version
    - Auditable: All changes logged in state_changelog
    - Recoverable: Can rollback to any previous version
    """
    
    # ===== Identity & Version Control =====
    project_id: str
    state_version: int  # Incremented on every commit (optimistic locking)
    phase: WorkflowPhase
    created_at: str
    updated_at: str
    
    # ===== Supervisor Routing =====
    next_node: Optional[str]  # Next node to execute (set by supervisor)
    supervisor_reason: Optional[str]  # Reason for routing decision
    
    # ===== MCP & Context =====
    mcp_request_profile: Optional[Dict[str, Any]]
    context_pack: Optional[Dict[str, Any]]
    normalized_docs: Annotated[List[Dict[str, Any]], merge_lists]
    context_source: Optional[str]  # "mcp" or "qdrant"
    
    # ===== Extraction Results =====
    extracted_facts: Optional[Dict[str, Any]]
    confidence_scores: Optional[Dict[str, float]]
    evidence_map: Optional[Dict[str, List[str]]]
    
    # ===== Questionnaire =====
    missing_questions: Annotated[List[Dict[str, Any]], merge_lists]
    question_priorities: Optional[Dict[str, int]]
    answered_questions: Annotated[List[Dict[str, Any]], merge_lists]
    gap_analysis: Optional[Dict[str, Any]]  # Gap analysis summary
    
    # ===== Intake Draft =====
    intake_draft: Optional[Dict[str, Any]]
    human_reviewed: bool
    review_comments: Annotated[List[str], merge_lists]
    review_timestamp: Optional[str]
    reviewer_id: Optional[str]
    
    # ===== Migration Plan =====
    migration_plan: Optional[Dict[str, Any]]
    
    # ===== Validation =====
    validation_results: Optional[Dict[str, Any]]
    review_flags: Annotated[List[str], merge_lists]
    
    # ===== Traceability =====
    trace_metadata: Annotated[Dict[str, Any], merge_dicts]
    state_changelog: Annotated[List[StateChangelogEntry], merge_lists]
    last_committed_by: str
    last_committed_at: str
    
    # ===== Error Handling =====
    retry_count: int
    max_retries: int
    error_log: Annotated[List[Dict[str, Any]], merge_lists]
    last_error: Optional[str]
    
    # ===== Checkpointing =====
    last_checkpoint_version: int
    checkpoint_count: int


def create_initial_state(project_id: str) -> MigrationState:
    """
    Create initial state for a new workflow.
    
    Args:
        project_id: Unique project identifier
        
    Returns:
        Initialized MigrationState
    """
    now = datetime.utcnow().isoformat()
    
    return MigrationState(
        # Identity & Version
        project_id=project_id,
        state_version=0,
        phase=WorkflowPhase.INIT,
        created_at=now,
        updated_at=now,
        
        # Supervisor Routing
        next_node=None,
        supervisor_reason=None,
        
        # Context
        mcp_request_profile=None,
        context_pack=None,
        normalized_docs=[],
        context_source=None,
        
        # Extraction
        extracted_facts=None,
        confidence_scores=None,
        evidence_map=None,
        
        # Questionnaire
        missing_questions=[],
        question_priorities=None,
        answered_questions=[],
        gap_analysis=None,
        
        # Intake
        intake_draft=None,
        human_reviewed=False,
        review_comments=[],
        review_timestamp=None,
        reviewer_id=None,
        
        # Planning
        migration_plan=None,
        
        # Validation
        validation_results=None,
        review_flags=[],
        
        # Traceability
        trace_metadata={
            "initialized_at": now,
            "initialized_by": "system"
        },
        state_changelog=[],
        last_committed_by="system",
        last_committed_at=now,
        
        # Error Handling
        retry_count=0,
        max_retries=3,
        error_log=[],
        last_error=None,
        
        # Checkpointing
        last_checkpoint_version=0,
        checkpoint_count=0
    )


def create_changelog_entry(
    version: int,
    patch: Dict[str, Any],
    committed_by: str,
    previous_phase: WorkflowPhase,
    new_phase: WorkflowPhase,
    description: Optional[str] = None
) -> StateChangelogEntry:
    """
    Create a changelog entry for state audit trail.
    
    Args:
        version: New state version
        patch: State changes
        committed_by: Agent/user who made the change
        previous_phase: Phase before change
        new_phase: Phase after change
        description: Optional description of change
        
    Returns:
        StateChangelogEntry
    """
    return StateChangelogEntry(
        version=version,
        patch=patch,
        committed_by=committed_by,
        committed_at=datetime.utcnow().isoformat(),
        previous_phase=previous_phase.value,
        new_phase=new_phase.value,
        description=description
    )

# Made with Bob
