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
from ..agents.context_retrieval_agent import ContextRetrievalAgent
from ..agents.extraction_agent import ExtractionAgent
from ..agents.questionnaire_agent import QuestionnaireAgent
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
        supervisor: Optional[Supervisor] = None
    ):
        """
        Initialize workflow orchestrator.
        
        Args:
            state_manager: State manager instance
            supervisor: Supervisor instance
        """
        self.state_manager = state_manager
        # Initialize supervisor synchronously if not provided
        self.supervisor = supervisor if supervisor is not None else get_supervisor()
        self._state_manager_initialized = False
        self._supervisor_initialized = True  # Already initialized
        
        # Initialize agents
        self.context_retrieval_agent = ContextRetrievalAgent()
        self.extraction_agent = ExtractionAgent()
        self.questionnaire_agent = QuestionnaireAgent()
        
        # Build workflow graph
        self.graph = self._build_graph()
        self.checkpointer = MemorySaver()
        self.workflow = self.graph.compile(checkpointer=self.checkpointer)
        
        logger.info(f"WorkflowOrchestrator initialized with supervisor: {self.supervisor is not None}")
    
    async def _ensure_state_manager(self):
        """Lazy initialize state manager."""
        if not self._state_manager_initialized:
            if self.state_manager is None:
                self.state_manager = await get_state_manager()
            self._state_manager_initialized = True
    
    async def _ensure_supervisor(self):
        """Lazy initialize supervisor."""
        if not self._supervisor_initialized:
            if self.supervisor is None:
                self.supervisor = get_supervisor()  # Not async
                logger.info(f"Supervisor initialized: {self.supervisor is not None}")
            self._supervisor_initialized = True
        
        # Double-check supervisor is not None
        if self.supervisor is None:
            logger.error("Supervisor is None after initialization attempt")
            self.supervisor = get_supervisor()
            logger.info(f"Supervisor re-initialized: {self.supervisor is not None}")
    
    
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
        # Ensure state manager is initialized
        await self._ensure_state_manager()
        
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
        # Ensure state manager is initialized
        await self._ensure_state_manager()
        
        # PRE-EXECUTION VALIDATION: Verify project exists and has documents
        logger.info(f"Validating project before execution: {project_id}")
        await self._validate_project_exists(project_id)
        
        # Get current state
        state = await self.state_manager.get_state(project_id)
        
        # If state doesn't exist, initialize it first
        if state is None:
            logger.info(f"State not found for project {project_id}, initializing...")
            state = await self.state_manager.initialize_state(project_id)
        
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
        # Ensure state manager is initialized
        await self._ensure_state_manager()
        
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
    
    async def _validate_project_exists(self, project_id: str) -> None:
        """
        Validate that project exists and has documents before starting workflow.
        
        Args:
            project_id: Project to validate
            
        Raises:
            ValueError: If project doesn't exist or has no documents
        """
        from ..storage.qdrant_store import QdrantStore
        
        try:
            # Initialize Qdrant store
            qdrant_store = QdrantStore()
            await qdrant_store.initialize()
            
            collection_name = f"project_{project_id}"
            
            # Check if collection exists and has documents
            try:
                count_result = qdrant_store.client.count(
                    collection_name=collection_name,
                    exact=True
                )
                
                doc_count = count_result.count if count_result else 0
                
                if doc_count == 0:
                    raise ValueError(
                        f"Project '{project_id}' has no documents. "
                        f"Please upload documents before starting workflow."
                    )
                
                logger.info(
                    f"Project validation passed: {project_id} has {doc_count} documents"
                )
                
            except Exception as e:
                if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                    raise ValueError(
                        f"Project '{project_id}' not found. "
                        f"Please upload documents first."
                    )
                raise
                
        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Project validation failed: {str(e)}")
            raise ValueError(f"Failed to validate project '{project_id}': {str(e)}")
    
    # Node implementations
    
    async def _supervisor_node(self, state: MigrationState) -> Dict[str, Any]:
        """Supervisor node: decide next step."""
        try:
            # Ensure supervisor is initialized
            await self._ensure_supervisor()
            
            logger.info(f"[supervisor_node] Current phase: {state['phase']}, version: {state['state_version']}")
            
            if self.supervisor is None:
                logger.error("[supervisor_node] Supervisor is None!")
                raise RuntimeError("Supervisor not initialized")
            
            decision = await self.supervisor.decide_next_node(state)
            
            logger.info(f"[supervisor_node] Decision: next_node={decision.next_node}, reason={decision.reason}")
            
            # Return state update - LangGraph will merge this automatically
            return {
                "next_node": decision.next_node,
                "supervisor_reason": decision.reason,
                "state_version": state["state_version"] + 1,
                "updated_at": datetime.utcnow().isoformat(),
                "last_committed_by": "supervisor",
                "last_committed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"[supervisor_node] Error: {e}", exc_info=True)
            raise
    
    async def _context_retrieval_node(self, state: MigrationState) -> Dict[str, Any]:
        """Context retrieval node: fetch context from MCP/Qdrant."""
        project_id = state["project_id"]
        logger.info(f"[context_retrieval_node] Retrieving context for project: {project_id}")
        
        # Execute context retrieval agent - uses execute(state) pattern like other agents
        agent_patch = await self.context_retrieval_agent.execute(state)
        
        logger.info(
            f"[context_retrieval_node] Context retrieval completed. "
            f"Documents: {len(agent_patch.get('normalized_docs', []))}"
        )
        
        # Return state update - LangGraph will merge this automatically
        return {
            **agent_patch,
            "phase": WorkflowPhase.CONTEXT_RETRIEVAL.value,
            "state_version": state["state_version"] + 1,
            "updated_at": datetime.utcnow().isoformat(),
            "last_committed_by": "context_retrieval_agent",
            "last_committed_at": datetime.utcnow().isoformat()
        }
    
    async def _extraction_node(self, state: MigrationState) -> Dict[str, Any]:
        """Extraction node: extract facts from context using ExtractionAgent."""
        project_id = state["project_id"]
        logger.info(f"[extraction_node] Starting fact extraction for project: {project_id}")
        
        # Execute extraction agent
        agent_patch = await self.extraction_agent.execute(state)
        
        # Return state update - LangGraph will merge this automatically
        return {
            **agent_patch,
            "phase": WorkflowPhase.EXTRACTION.value,
            "state_version": state["state_version"] + 1,
            "updated_at": datetime.utcnow().isoformat(),
            "last_committed_by": "extraction_agent",
            "last_committed_at": datetime.utcnow().isoformat()
        }
    
    async def _questionnaire_node(self, state: MigrationState) -> Dict[str, Any]:
        """Questionnaire node: generate questions using QuestionnaireAgent."""
        project_id = state["project_id"]
        logger.info(f"[questionnaire_node] Starting question generation for project: {project_id}")
        
        # Execute questionnaire agent
        agent_patch = await self.questionnaire_agent.execute(state)
        
        # Return state update - LangGraph will merge this automatically
        return {
            **agent_patch,
            "phase": WorkflowPhase.QUESTIONNAIRE.value,
            "state_version": state["state_version"] + 1,
            "updated_at": datetime.utcnow().isoformat(),
            "last_committed_by": "questionnaire_agent",
            "last_committed_at": datetime.utcnow().isoformat()
        }
    
    async def _intake_draft_node(self, state: MigrationState) -> Dict[str, Any]:
        """Intake draft node: generate intake document."""
        # Placeholder: will be implemented in Phase 5
        return {
            "intake_draft": {"placeholder": "Phase 5 implementation"},
            "phase": WorkflowPhase.INTAKE_DRAFT.value,
            "state_version": state["state_version"] + 1,
            "updated_at": datetime.utcnow().isoformat(),
            "last_committed_by": "intake_draft_agent",
            "last_committed_at": datetime.utcnow().isoformat()
        }
    
    async def _human_review_node(self, state: MigrationState) -> Dict[str, Any]:
        """Human review node: pause for human review."""
        # Placeholder: will be implemented in Phase 5
        return {
            "phase": WorkflowPhase.HUMAN_REVIEW.value,
            "state_version": state["state_version"] + 1,
            "updated_at": datetime.utcnow().isoformat(),
            "last_committed_by": "human_review_gate",
            "last_committed_at": datetime.utcnow().isoformat()
        }
    
    async def _migration_planning_node(self, state: MigrationState) -> Dict[str, Any]:
        """Migration planning node: generate migration plan."""
        # Placeholder: will be implemented in Phase 6
        return {
            "migration_plan": {"placeholder": "Phase 6 implementation"},
            "phase": WorkflowPhase.MIGRATION_PLANNING.value,
            "state_version": state["state_version"] + 1,
            "updated_at": datetime.utcnow().isoformat(),
            "last_committed_by": "migration_planning_agent",
            "last_committed_at": datetime.utcnow().isoformat()
        }
    
    async def _validation_node(self, state: MigrationState) -> Dict[str, Any]:
        """Validation node: validate final output."""
        # Placeholder: will be implemented in Phase 6
        return {
            "validation_results": {"placeholder": "Phase 6 implementation"},
            "phase": WorkflowPhase.VALIDATION.value,
            "state_version": state["state_version"] + 1,
            "updated_at": datetime.utcnow().isoformat(),
            "last_committed_by": "validation_agent",
            "last_committed_at": datetime.utcnow().isoformat()
        }
    
    async def _complete_node(self, state: MigrationState) -> Dict[str, Any]:
        """Complete node: finalize workflow."""
        return {
            "phase": WorkflowPhase.COMPLETE.value,
            "state_version": state["state_version"] + 1,
            "updated_at": datetime.utcnow().isoformat(),
            "last_committed_by": "workflow_orchestrator",
            "last_committed_at": datetime.utcnow().isoformat()
        }
    
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
