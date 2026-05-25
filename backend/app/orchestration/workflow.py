"""
LangGraph Workflow

Supervisor-led multi-agent orchestration with transactional state management.
Follows SOLID principles with clean agent boundaries.
"""

import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import MigrationState, WorkflowPhase, create_initial_state
from .state_manager import StateManager, get_state_manager
from .supervisor import Supervisor, get_supervisor
from .context_retrieval import ContextRetriever, get_context_retriever
from ..tracing.langsmith import trace_operation

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    LangGraph workflow orchestrator.
    
    Responsibilities:
    - Build LangGraph workflow
    - Execute workflow with checkpointing
    - Manage state transitions
    - Handle pauses and resumes
    
    Design Principles:
    - SOLID: Single responsibility (orchestration only)
    - KISS: Simple graph structure
    - DRY: Reusable node wrappers
    """
    
    def __init__(
        self,
        state_manager: Optional[StateManager] = None,
        supervisor: Optional[Supervisor] = None,
        context_retrieval: Optional[ContextRetriever] = None
    ):
        """
        Initialize workflow orchestrator.
        
        Args:
            state_manager: State manager instance
            supervisor: Supervisor instance
            context_retrieval: Context retrieval instance
        """
        self.state_manager = state_manager or get_state_manager()
        self.supervisor = supervisor or get_supervisor()
        self.context_retrieval = context_retrieval
        self._context_retrieval_initialized = False
        
        # Build workflow graph
        self.graph = self._build_graph()
        self.checkpointer = MemorySaver()
        self.workflow = self.graph.compile(checkpointer=self.checkpointer)
    
    async def _ensure_context_retrieval(self):
        """Lazy initialize context retrieval."""
        if not self._context_retrieval_initialized:
            if self.context_retrieval is None:
                self.context_retrieval = await get_context_retriever()
            self._context_retrieval_initialized = True
    
    def _build_graph(self) -> StateGraph:
        """
        Build LangGraph workflow.
        
        Graph structure:
        - START → supervisor
        - supervisor → context_retrieval | extraction | questionnaire | intake_draft | human_review | migration_planning | validation | END
        - Each node → supervisor (for routing)
        
        Returns:
            StateGraph instance
        """
        # Create graph with MigrationState schema
        graph = StateGraph(MigrationState)
        
        # Add nodes (use _node suffix to avoid conflicts with state attributes)
        graph.add_node("supervisor", self._supervisor_node)
        graph.add_node("context_retrieval_node", self._context_retrieval_node)
        graph.add_node("extraction_node", self._extraction_node)
        graph.add_node("questionnaire_node", self._questionnaire_node)
        graph.add_node("intake_draft_node", self._intake_draft_node)
        graph.add_node("human_review_node", self._human_review_node)
        graph.add_node("migration_planning_node", self._migration_planning_node)
        graph.add_node("validation_node", self._validation_node)
        graph.add_node("complete_node", self._complete_node)
        
        # Set entry point
        graph.set_entry_point("supervisor")
        
        # Add conditional edges from supervisor
        graph.add_conditional_edges(
            "supervisor",
            self._route_from_supervisor,
            {
                "context_retrieval": "context_retrieval_node",
                "extraction": "extraction_node",
                "questionnaire": "questionnaire_node",
                "intake_draft": "intake_draft_node",
                "human_review": "human_review_node",
                "migration_planning": "migration_planning_node",
                "validation": "validation_node",
                "complete": "complete_node",
                "END": END
            }
        )
        
        # Add edges back to supervisor from each node
        for node in [
            "context_retrieval_node",
            "extraction_node",
            "questionnaire_node",
            "intake_draft_node",
            "human_review_node",
            "migration_planning_node",
            "validation_node",
            "complete_node"
        ]:
            graph.add_edge(node, "supervisor")
        
        return graph
    
    @trace_operation("workflow_start", run_type="chain", tags=["workflow", "start"])
    async def start_workflow(
        self,
        project_id: str,
        mcp_profile: str = "context_retrieval_profile",
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start new workflow.
        
        Args:
            project_id: Project identifier
            mcp_profile: MCP retrieval profile
            query: Optional search query
            
        Returns:
            Initial state
        """
        # Initialize state
        initial_state = await self.state_manager.initialize_state(project_id)
        
        # Update with MCP profile
        if mcp_profile or query:
            patch = {
                "mcp_request_profile": {
                    "profile_name": mcp_profile,
                    "query": query
                }
            }
            initial_state = await self.state_manager.commit_state(
                project_id=project_id,
                patch=patch,
                expected_version=0,
                committed_by="workflow_orchestrator"
            )
        
        logger.info(f"Workflow started for project: {project_id}")
        
        return initial_state
    
    @trace_operation("workflow_execute", run_type="chain", tags=["workflow", "execute"])
    async def execute_workflow(
        self,
        project_id: str,
        config: Optional[Dict[str, Any]] = None
    ) -> MigrationState:
        """
        Execute workflow for project.
        
        Args:
            project_id: Project identifier
            config: Optional LangGraph config
            
        Returns:
            Final state
        """
        # Get current state
        state = await self.state_manager.get_state(project_id)
        
        # Execute workflow
        config = config or {"configurable": {"thread_id": project_id}}
        
        logger.info(f"Executing workflow for project: {project_id}")
        
        # Run workflow
        final_state = await self.workflow.ainvoke(state, config)
        
        logger.info(f"Workflow completed for project: {project_id}")
        
        return final_state
    
    @trace_operation("workflow_resume", run_type="chain", tags=["workflow", "resume"])
    async def resume_workflow(
        self,
        project_id: str,
        updates: Optional[Dict[str, Any]] = None
    ) -> MigrationState:
        """
        Resume paused workflow.
        
        Args:
            project_id: Project identifier
            updates: Optional state updates (e.g., human review approval)
            
        Returns:
            Updated state
        """
        # Get current state
        state = await self.state_manager.get_state(project_id)
        current_version = state["state_version"]
        
        # Apply updates if provided
        if updates:
            patch = {
                **updates,
                "last_committed_at": datetime.utcnow().isoformat()
            }
            
            state = await self.state_manager.commit_state(
                project_id=project_id,
                patch=patch,
                expected_version=current_version,
                committed_by="human_reviewer"
            )
        
        # Resume execution
        return await self.execute_workflow(project_id)
    
    # Node implementations
    
    async def _supervisor_node(self, state: MigrationState) -> MigrationState:
        """Supervisor node: decide next step."""
        decision = await self.supervisor.decide_next_node(state)
        
        # Update state with decision
        patch = {
            "next_node": decision.next_node,
            "supervisor_reason": decision.reason,
            "last_committed_by": "supervisor",
            "last_committed_at": datetime.utcnow().isoformat()
        }
        
        # Commit state
        updated_state = await self.state_manager.commit_state(
            project_id=state["project_id"],
            patch=patch,
            expected_version=state["state_version"],
            committed_by="supervisor"
        )
        
        return updated_state
    
    async def _context_retrieval_node(self, state: MigrationState) -> MigrationState:
        """Context retrieval node: fetch context from MCP/Qdrant."""
        await self._ensure_context_retrieval()
        
        project_id = state["project_id"]
        mcp_profile = state.get("mcp_request_profile") or {}
        profile_name = mcp_profile.get("profile_name", "context_retrieval_profile")
        query = mcp_profile.get("query")
        
        # Retrieve context
        assert self.context_retrieval is not None
        context_pack = await self.context_retrieval.retrieve(
            project_id=project_id,
            profile_name=profile_name,
            query=query
        )
        
        # Update state
        patch = {
            "context_pack": context_pack.model_dump(),
            "phase": WorkflowPhase.CONTEXT_RETRIEVAL.value,
            "last_committed_by": "context_retrieval_agent",
            "last_committed_at": datetime.utcnow().isoformat()
        }
        
        # Commit state
        updated_state = await self.state_manager.commit_state(
            project_id=project_id,
            patch=patch,
            expected_version=state["state_version"],
            committed_by="context_retrieval_agent"
        )
        
        return updated_state
    
    async def _extraction_node(self, state: MigrationState) -> MigrationState:
        """Extraction node: extract facts from context."""
        # Placeholder: will be implemented in Phase 4
        patch = {
            "extracted_facts": {"placeholder": "Phase 4 implementation"},
            "phase": WorkflowPhase.EXTRACTION.value,
            "last_committed_by": "extraction_agent",
            "last_committed_at": datetime.utcnow().isoformat()
        }
        
        updated_state = await self.state_manager.commit_state(
            project_id=state["project_id"],
            patch=patch,
            expected_version=state["state_version"],
            committed_by="extraction_agent"
        )
        
        return updated_state
    
    async def _questionnaire_node(self, state: MigrationState) -> MigrationState:
        """Questionnaire node: generate questions."""
        # Placeholder: will be implemented in Phase 4
        patch = {
            "missing_questions": [{"placeholder": "Phase 4 implementation"}],
            "phase": WorkflowPhase.QUESTIONNAIRE.value,
            "last_committed_by": "questionnaire_agent",
            "last_committed_at": datetime.utcnow().isoformat()
        }
        
        updated_state = await self.state_manager.commit_state(
            project_id=state["project_id"],
            patch=patch,
            expected_version=state["state_version"],
            committed_by="questionnaire_agent"
        )
        
        return updated_state
    
    async def _intake_draft_node(self, state: MigrationState) -> MigrationState:
        """Intake draft node: generate intake document."""
        # Placeholder: will be implemented in Phase 5
        patch = {
            "intake_draft": {"placeholder": "Phase 5 implementation"},
            "phase": WorkflowPhase.INTAKE_DRAFT.value,
            "last_committed_by": "intake_draft_agent",
            "last_committed_at": datetime.utcnow().isoformat()
        }
        
        updated_state = await self.state_manager.commit_state(
            project_id=state["project_id"],
            patch=patch,
            expected_version=state["state_version"],
            committed_by="intake_draft_agent"
        )
        
        return updated_state
    
    async def _human_review_node(self, state: MigrationState) -> MigrationState:
        """Human review node: pause for human review."""
        # Placeholder: will be implemented in Phase 5
        patch = {
            "phase": WorkflowPhase.HUMAN_REVIEW.value,
            "last_committed_by": "human_review_gate",
            "last_committed_at": datetime.utcnow().isoformat()
        }
        
        updated_state = await self.state_manager.commit_state(
            project_id=state["project_id"],
            patch=patch,
            expected_version=state["state_version"],
            committed_by="human_review_gate"
        )
        
        return updated_state
    
    async def _migration_planning_node(self, state: MigrationState) -> MigrationState:
        """Migration planning node: generate migration plan."""
        # Placeholder: will be implemented in Phase 6
        patch = {
            "migration_plan": {"placeholder": "Phase 6 implementation"},
            "phase": WorkflowPhase.MIGRATION_PLANNING.value,
            "last_committed_by": "migration_planning_agent",
            "last_committed_at": datetime.utcnow().isoformat()
        }
        
        updated_state = await self.state_manager.commit_state(
            project_id=state["project_id"],
            patch=patch,
            expected_version=state["state_version"],
            committed_by="migration_planning_agent"
        )
        
        return updated_state
    
    async def _validation_node(self, state: MigrationState) -> MigrationState:
        """Validation node: validate final output."""
        # Placeholder: will be implemented in Phase 6
        patch = {
            "validation_results": {"placeholder": "Phase 6 implementation"},
            "phase": WorkflowPhase.VALIDATION.value,
            "last_committed_by": "validation_agent",
            "last_committed_at": datetime.utcnow().isoformat()
        }
        
        updated_state = await self.state_manager.commit_state(
            project_id=state["project_id"],
            patch=patch,
            expected_version=state["state_version"],
            committed_by="validation_agent"
        )
        
        return updated_state
    
    async def _complete_node(self, state: MigrationState) -> MigrationState:
        """Complete node: finalize workflow."""
        patch = {
            "phase": WorkflowPhase.COMPLETE.value,
            "last_committed_by": "workflow_orchestrator",
            "last_committed_at": datetime.utcnow().isoformat()
        }
        
        updated_state = await self.state_manager.commit_state(
            project_id=state["project_id"],
            patch=patch,
            expected_version=state["state_version"],
            committed_by="workflow_orchestrator"
        )
        
        return updated_state
    
    def _route_from_supervisor(self, state: MigrationState) -> str:
        """
        Route from supervisor based on next_node.
        
        Args:
            state: Current state
            
        Returns:
            Next node name
        """
        next_node = state.get("next_node", "END")
        logger.info(f"Routing to: {next_node}")
        return next_node


# Singleton instance
_orchestrator: Optional[WorkflowOrchestrator] = None


def get_workflow_orchestrator() -> WorkflowOrchestrator:
    """
    Get or create WorkflowOrchestrator singleton.
    
    Returns:
        WorkflowOrchestrator instance
    """
    global _orchestrator
    
    if _orchestrator is None:
        _orchestrator = WorkflowOrchestrator()
    
    return _orchestrator

# Made with Bob
