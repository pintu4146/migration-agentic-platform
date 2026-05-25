"""
Supervisor Node

Controls workflow routing and phase transitions.
Follows SOLID principles with clear decision logic.
"""

import logging
from typing import Dict, Any, Optional

from .state import MigrationState, WorkflowPhase
from ..tracing.langsmith import trace_operation

logger = logging.getLogger(__name__)


class SupervisorDecision:
    """
    Supervisor routing decision.
    
    Encapsulates the next node and phase transition.
    """
    
    def __init__(
        self,
        next_node: str,
        next_phase: WorkflowPhase,
        reason: str
    ):
        """
        Initialize supervisor decision.
        
        Args:
            next_node: Next node to execute
            next_phase: Next workflow phase
            reason: Reason for decision
        """
        self.next_node = next_node
        self.next_phase = next_phase
        self.reason = reason
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "next_node": self.next_node,
            "next_phase": self.next_phase.value,
            "reason": self.reason
        }


class Supervisor:
    """
    Workflow supervisor node.
    
    Responsibilities:
    - Analyze current state
    - Decide next node
    - Manage phase transitions
    - Handle errors and retries
    
    Design Principles:
    - SOLID: Single responsibility (routing only)
    - KISS: Simple decision tree
    - DRY: Reusable decision logic
    """
    
    @trace_operation("supervisor_decide", run_type="chain", tags=["supervisor", "routing"])
    async def decide_next_node(
        self,
        state: MigrationState
    ) -> SupervisorDecision:
        """
        Decide next node based on current state.
        
        Decision tree:
        1. INIT → context_retrieval
        2. CONTEXT_RETRIEVAL → extraction
        3. EXTRACTION → questionnaire
        4. QUESTIONNAIRE → intake_draft
        5. INTAKE_DRAFT → human_review
        6. HUMAN_REVIEW → migration_planning (if approved)
        7. MIGRATION_PLANNING → validation
        8. VALIDATION → complete
        9. ERROR → retry or fail
        
        Args:
            state: Current workflow state
            
        Returns:
            SupervisorDecision with next node and phase
        """
        current_phase = WorkflowPhase(state["phase"])
        
        # Check for errors
        if current_phase == WorkflowPhase.ERROR:
            return await self._handle_error(state)
        
        # Normal flow
        if current_phase == WorkflowPhase.INIT:
            return SupervisorDecision(
                next_node="context_retrieval",
                next_phase=WorkflowPhase.CONTEXT_RETRIEVAL,
                reason="Starting workflow: retrieve context"
            )
        
        elif current_phase == WorkflowPhase.CONTEXT_RETRIEVAL:
            if not state.get("context_pack"):
                return SupervisorDecision(
                    next_node="context_retrieval",
                    next_phase=WorkflowPhase.CONTEXT_RETRIEVAL,
                    reason="Retry: context not retrieved"
                )
            return SupervisorDecision(
                next_node="extraction",
                next_phase=WorkflowPhase.EXTRACTION,
                reason="Context retrieved: extract facts"
            )
        
        elif current_phase == WorkflowPhase.EXTRACTION:
            if not state.get("extracted_facts"):
                return SupervisorDecision(
                    next_node="extraction",
                    next_phase=WorkflowPhase.EXTRACTION,
                    reason="Retry: facts not extracted"
                )
            return SupervisorDecision(
                next_node="questionnaire",
                next_phase=WorkflowPhase.QUESTIONNAIRE,
                reason="Facts extracted: generate questions"
            )
        
        elif current_phase == WorkflowPhase.QUESTIONNAIRE:
            return SupervisorDecision(
                next_node="intake_draft",
                next_phase=WorkflowPhase.INTAKE_DRAFT,
                reason="Questions generated: draft intake"
            )
        
        elif current_phase == WorkflowPhase.INTAKE_DRAFT:
            if not state.get("intake_draft"):
                return SupervisorDecision(
                    next_node="intake_draft",
                    next_phase=WorkflowPhase.INTAKE_DRAFT,
                    reason="Retry: intake not drafted"
                )
            return SupervisorDecision(
                next_node="human_review",
                next_phase=WorkflowPhase.HUMAN_REVIEW,
                reason="Intake drafted: await human review"
            )
        
        elif current_phase == WorkflowPhase.HUMAN_REVIEW:
            if not state.get("human_reviewed"):
                return SupervisorDecision(
                    next_node="human_review",
                    next_phase=WorkflowPhase.HUMAN_REVIEW,
                    reason="Waiting: human review pending"
                )
            return SupervisorDecision(
                next_node="migration_planning",
                next_phase=WorkflowPhase.MIGRATION_PLANNING,
                reason="Review approved: generate migration plan"
            )
        
        elif current_phase == WorkflowPhase.MIGRATION_PLANNING:
            if not state.get("migration_plan"):
                return SupervisorDecision(
                    next_node="migration_planning",
                    next_phase=WorkflowPhase.MIGRATION_PLANNING,
                    reason="Retry: plan not generated"
                )
            return SupervisorDecision(
                next_node="validation",
                next_phase=WorkflowPhase.VALIDATION,
                reason="Plan generated: validate output"
            )
        
        elif current_phase == WorkflowPhase.VALIDATION:
            return SupervisorDecision(
                next_node="complete",
                next_phase=WorkflowPhase.COMPLETE,
                reason="Validation complete: workflow finished"
            )
        
        elif current_phase == WorkflowPhase.COMPLETE:
            return SupervisorDecision(
                next_node="END",
                next_phase=WorkflowPhase.COMPLETE,
                reason="Workflow complete"
            )
        
        else:
            logger.error(f"Unknown phase: {current_phase}")
            return SupervisorDecision(
                next_node="END",
                next_phase=WorkflowPhase.ERROR,
                reason=f"Unknown phase: {current_phase}"
            )
    
    async def _handle_error(
        self,
        state: MigrationState
    ) -> SupervisorDecision:
        """
        Handle error state.
        
        Args:
            state: Current state
            
        Returns:
            SupervisorDecision for error handling
        """
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 3)
        
        if retry_count < max_retries:
            logger.warning(
                f"Error in workflow (retry {retry_count + 1}/{max_retries})"
            )
            # Retry from last successful phase
            last_phase = self._get_last_successful_phase(state)
            return SupervisorDecision(
                next_node=self._phase_to_node(last_phase),
                next_phase=last_phase,
                reason=f"Retry from {last_phase.value}"
            )
        else:
            logger.error(
                f"Max retries ({max_retries}) exceeded. Workflow failed."
            )
            return SupervisorDecision(
                next_node="END",
                next_phase=WorkflowPhase.ERROR,
                reason="Max retries exceeded"
            )
    
    def _get_last_successful_phase(
        self,
        state: MigrationState
    ) -> WorkflowPhase:
        """Get last successful phase from changelog."""
        changelog = state.get("state_changelog", [])
        if not changelog:
            return WorkflowPhase.INIT
        
        # Find last non-error phase
        for entry in reversed(changelog):
            phase = WorkflowPhase(entry["new_phase"])
            if phase != WorkflowPhase.ERROR:
                return phase
        
        return WorkflowPhase.INIT
    
    def _phase_to_node(self, phase: WorkflowPhase) -> str:
        """Convert phase to node name."""
        phase_to_node_map = {
            WorkflowPhase.INIT: "context_retrieval",
            WorkflowPhase.CONTEXT_RETRIEVAL: "context_retrieval",
            WorkflowPhase.EXTRACTION: "extraction",
            WorkflowPhase.QUESTIONNAIRE: "questionnaire",
            WorkflowPhase.INTAKE_DRAFT: "intake_draft",
            WorkflowPhase.HUMAN_REVIEW: "human_review",
            WorkflowPhase.MIGRATION_PLANNING: "migration_planning",
            WorkflowPhase.VALIDATION: "validation",
            WorkflowPhase.COMPLETE: "END",
            WorkflowPhase.ERROR: "END",
        }
        return phase_to_node_map.get(phase, "END")


# Singleton instance
_supervisor: Optional[Supervisor] = None


def get_supervisor() -> Supervisor:
    """
    Get or create Supervisor singleton.
    
    Returns:
        Supervisor instance
    """
    global _supervisor
    
    if _supervisor is None:
        _supervisor = Supervisor()
    
    return _supervisor

# Made with Bob
