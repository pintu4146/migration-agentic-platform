# Phase 3: LangGraph Orchestration & Transactional State Management

## Overview

Phase 3 implements the core orchestration engine using LangGraph with a supervisor-led workflow pattern. This phase focuses on transactional state management with optimistic locking, comprehensive LangSmith tracing, and deterministic workflow execution.

## Objectives

1. Implement LangGraph workflow with supervisor pattern
2. Create transactional state manager with optimistic locking
3. Build state versioning and changelog system
4. Integrate LangSmith tracing for all transitions
5. Implement checkpointing and pause/resume
6. Create conditional routing logic
7. Add retry and error handling
8. Build state recovery mechanisms

## Critical Requirements

### Transactional State Management

**MUST HAVE:**
- Optimistic locking with version control
- Single commit at a time (no concurrent writes)
- Write-ahead logging (changelog)
- Atomic state updates
- Rollback capability
- State validation before commit

**MUST NOT:**
- Allow concurrent state modifications
- Skip version checks
- Lose state history
- Allow partial commits

### LangSmith Tracing

**MUST TRACE:**
- Every node execution
- Every state transition
- Every agent decision
- Every state commit
- Every retry attempt
- Every error occurrence

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Workflow                        │
│                                                              │
│  ┌──────────────┐                                           │
│  │  Supervisor  │◄──────────────────────┐                  │
│  │    Node      │                        │                  │
│  └──────┬───────┘                        │                  │
│         │                                 │                  │
│         │ Route Decision                  │                  │
│         │                                 │                  │
│    ┌────▼────────────────────────────┐  │                  │
│    │   Conditional Edge Router       │  │                  │
│    └────┬────────────────────────────┘  │                  │
│         │                                 │                  │
│    ┌────▼─────┐  ┌──────────┐  ┌───────▼──┐  ┌──────────┐│
│    │ Context  │  │Extraction│  │Questionnaire│ │ Intake  ││
│    │Retrieval │  │  Agent   │  │   Agent    │  │  Draft  ││
│    └────┬─────┘  └────┬─────┘  └─────┬─────┘  └────┬─────┘│
│         │             │               │              │       │
│         └─────────────┴───────────────┴──────────────┘       │
│                         │                                     │
│                         │ Return to Supervisor               │
│                         │                                     │
└─────────────────────────┼─────────────────────────────────────┘
                          │
                          ▼
        ┌─────────────────────────────────────┐
        │   Transactional State Manager       │
        │                                      │
        │  ┌────────────────────────────────┐ │
        │  │  Optimistic Locking            │ │
        │  │  - Version Check               │ │
        │  │  - Atomic Commit               │ │
        │  │  - Changelog Recording         │ │
        │  └────────────────────────────────┘ │
        │                                      │
        │  ┌────────────────────────────────┐ │
        │  │  State Validation              │ │
        │  │  - Schema Check                │ │
        │  │  - Integrity Verification      │ │
        │  └────────────────────────────────┘ │
        │                                      │
        │  ┌────────────────────────────────┐ │
        │  │  Checkpoint Management         │ │
        │  │  - Snapshot Creation           │ │
        │  │  - Recovery Points             │ │
        │  └────────────────────────────────┘ │
        └──────────────┬───────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────────────┐
        │      LangSmith Tracing               │
        │  - State Transitions                 │
        │  - Node Executions                   │
        │  - Version Changes                   │
        │  - Commit Operations                 │
        └──────────────────────────────────────┘
```

## State Schema

```python
# backend/app/orchestration/state.py
from typing import TypedDict, Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

class WorkflowPhase(str, Enum):
    """Workflow execution phases"""
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
    """Single changelog entry"""
    version: int
    patch: Dict[str, Any]
    committed_by: str
    committed_at: str
    previous_phase: str
    new_phase: str

class MigrationState(TypedDict):
    """Complete workflow state with version control"""
    
    # ===== Identity & Version Control =====
    project_id: str
    state_version: int  # Incremented on every commit
    phase: WorkflowPhase
    created_at: str
    updated_at: str
    
    # ===== MCP & Context =====
    mcp_request_profile: Optional[Dict[str, Any]]
    context_pack: Optional[Dict[str, Any]]
    normalized_docs: List[Dict[str, Any]]
    
    # ===== Extraction Results =====
    extracted_facts: Optional[Dict[str, Any]]
    confidence_scores: Optional[Dict[str, float]]
    evidence_map: Optional[Dict[str, List[str]]]
    
    # ===== Questionnaire =====
    missing_questions: List[Dict[str, Any]]
    question_priorities: Optional[Dict[str, int]]
    answered_questions: List[Dict[str, Any]]
    
    # ===== Intake Draft =====
    intake_draft: Optional[Dict[str, Any]]
    human_reviewed: bool
    review_comments: List[str]
    review_timestamp: Optional[str]
    
    # ===== Migration Plan =====
    migration_plan: Optional[Dict[str, Any]]
    
    # ===== Validation =====
    validation_results: Optional[Dict[str, Any]]
    review_flags: List[str]
    
    # ===== Traceability =====
    trace_metadata: Dict[str, Any]
    state_changelog: List[StateChangelogEntry]
    last_committed_by: str
    last_committed_at: str
    
    # ===== Error Handling =====
    retry_count: int
    max_retries: int
    error_log: List[Dict[str, Any]]
    last_error: Optional[str]
```

## Transactional State Manager

```python
# backend/app/orchestration/state_manager.py
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
from copy import deepcopy
import json
import logging

logger = logging.getLogger(__name__)

class StateTransactionError(Exception):
    """Raised when state transaction fails"""
    pass

class StateValidationError(Exception):
    """Raised when state validation fails"""
    pass

class StateManager:
    """
    Transactional state manager with optimistic locking.
    
    Key Features:
    - Optimistic locking via version numbers
    - Write-ahead logging (changelog)
    - Atomic commits
    - State validation
    - Recovery from checkpoints
    """
    
    def __init__(self, tracer: Optional['LangSmithTracer'] = None):
        self._state: Optional[MigrationState] = None
        self._lock = asyncio.Lock()
        self.tracer = tracer
        self._checkpoint_interval = 5  # Checkpoint every 5 commits
        self._checkpoints: List[MigrationState] = []
    
    async def initialize_state(self, project_id: str) -> MigrationState:
        """
        Initialize new state with version 0.
        
        Args:
            project_id: Unique project identifier
            
        Returns:
            Initialized state
        """
        async with self._lock:
            now = datetime.utcnow().isoformat()
            
            self._state = MigrationState(
                # Identity & Version
                project_id=project_id,
                state_version=0,
                phase=WorkflowPhase.INIT,
                created_at=now,
                updated_at=now,
                
                # Context
                mcp_request_profile=None,
                context_pack=None,
                normalized_docs=[],
                
                # Extraction
                extracted_facts=None,
                confidence_scores=None,
                evidence_map=None,
                
                # Questionnaire
                missing_questions=[],
                question_priorities=None,
                answered_questions=[],
                
                # Intake
                intake_draft=None,
                human_reviewed=False,
                review_comments=[],
                review_timestamp=None,
                
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
                last_error=None
            )
            
            # Create initial checkpoint
            self._create_checkpoint()
            
            logger.info(f"Initialized state for project {project_id}")
            
            return deepcopy(self._state)
    
    async def read_state(self) -> MigrationState:
        """
        Read current state snapshot (non-blocking read).
        
        Returns:
            Deep copy of current state
            
        Raises:
            StateTransactionError: If state not initialized
        """
        async with self._lock:
            if self._state is None:
                raise StateTransactionError("State not initialized")
            return deepcopy(self._state)
    
    async def commit_state_patch(
        self,
        patch: Dict[str, Any],
        expected_version: int,
        committed_by: str,
        validate: bool = True
    ) -> MigrationState:
        """
        Commit state patch with optimistic locking.
        
        This is the ONLY way to modify state. All agents must use this method.
        
        Args:
            patch: Dictionary of fields to update
            expected_version: Expected current version (for optimistic locking)
            committed_by: Identifier of committer (agent name)
            validate: Whether to validate state after applying patch
            
        Returns:
            Updated state
            
        Raises:
            StateTransactionError: If version mismatch or state not initialized
            StateValidationError: If validation fails
        """
        async with self._lock:
            if self._state is None:
                raise StateTransactionError("State not initialized")
            
            # ===== OPTIMISTIC LOCKING: Version Check =====
            if self._state["state_version"] != expected_version:
                error_msg = (
                    f"Version mismatch: expected {expected_version}, "
                    f"current {self._state['state_version']}"
                )
                logger.error(error_msg)
                raise StateTransactionError(error_msg)
            
            # ===== RECORD CHANGELOG ENTRY (Write-Ahead Log) =====
            previous_phase = self._state["phase"]
            new_phase = patch.get("phase", previous_phase)
            
            changelog_entry: StateChangelogEntry = {
                "version": expected_version,
                "patch": deepcopy(patch),
                "committed_by": committed_by,
                "committed_at": datetime.utcnow().isoformat(),
                "previous_phase": previous_phase,
                "new_phase": new_phase
            }
            
            # ===== APPLY PATCH ATOMICALLY =====
            try:
                for key, value in patch.items():
                    if key in self._state:
                        self._state[key] = value
                    else:
                        logger.warning(f"Patch contains unknown key: {key}")
                
                # Update metadata
                self._state["state_version"] += 1
                self._state["last_committed_by"] = committed_by
                self._state["last_committed_at"] = changelog_entry["committed_at"]
                self._state["updated_at"] = changelog_entry["committed_at"]
                
                # Append to changelog
                self._state["state_changelog"].append(changelog_entry)
                
                # ===== VALIDATE STATE =====
                if validate:
                    self._validate_state()
                
                # ===== CREATE CHECKPOINT IF NEEDED =====
                if self._state["state_version"] % self._checkpoint_interval == 0:
                    self._create_checkpoint()
                
                # ===== TRACE STATE TRANSITION =====
                if self.tracer:
                    await self.tracer.trace_state_change(
                        from_phase=previous_phase,
                        to_phase=new_phase,
                        state_version=self._state["state_version"],
                        state_diff=patch,
                        committed_by=committed_by
                    )
                
                logger.info(
                    f"State committed: v{self._state['state_version']} "
                    f"by {committed_by}, phase: {previous_phase} -> {new_phase}"
                )
                
                return deepcopy(self._state)
                
            except Exception as e:
                # Rollback on error
                logger.error(f"State commit failed: {e}")
                raise StateTransactionError(f"Failed to commit state: {e}")
    
    def _validate_state(self):
        """
        Validate state integrity.
        
        Raises:
            StateValidationError: If validation fails
        """
        # Check required fields
        required_fields = ["project_id", "state_version", "phase"]
        for field in required_fields:
            if field not in self._state or self._state[field] is None:
                raise StateValidationError(f"Required field missing: {field}")
        
        # Check version is non-negative
        if self._state["state_version"] < 0:
            raise StateValidationError("State version cannot be negative")
        
        # Check phase is valid
        if self._state["phase"] not in WorkflowPhase.__members__.values():
            raise StateValidationError(f"Invalid phase: {self._state['phase']}")
        
        # Phase-specific validations
        if self._state["phase"] == WorkflowPhase.EXTRACTION:
            if not self._state["normalized_docs"]:
                raise StateValidationError("Extraction phase requires normalized_docs")
        
        if self._state["phase"] == WorkflowPhase.MIGRATION_PLANNING:
            if not self._state["human_reviewed"]:
                raise StateValidationError("Migration planning requires human review")
    
    def _create_checkpoint(self):
        """Create state checkpoint for recovery"""
        checkpoint = deepcopy(self._state)
        self._checkpoints.append(checkpoint)
        
        # Keep only last 10 checkpoints
        if len(self._checkpoints) > 10:
            self._checkpoints.pop(0)
        
        logger.info(f"Checkpoint created at version {self._state['state_version']}")
    
    async def get_changelog(self) -> List[StateChangelogEntry]:
        """
        Get full state changelog.
        
        Returns:
            List of changelog entries
        """
        async with self._lock:
            if self._state is None:
                return []
            return deepcopy(self._state["state_changelog"])
    
    async def rollback_to_version(self, target_version: int) -> MigrationState:
        """
        Rollback state to specific version using changelog.
        
        Args:
            target_version: Version to rollback to
            
        Returns:
            State at target version
            
        Raises:
            StateTransactionError: If rollback fails
        """
        async with self._lock:
            if self._state is None:
                raise StateTransactionError("State not initialized")
            
            # Find checkpoint closest to target version
            checkpoint = None
            for cp in reversed(self._checkpoints):
                if cp["state_version"] <= target_version:
                    checkpoint = cp
                    break
            
            if checkpoint is None:
                raise StateTransactionError(
                    f"No checkpoint found for version {target_version}"
                )
            
            # Restore from checkpoint
            self._state = deepcopy(checkpoint)
            
            # Replay changelog entries up to target version
            for entry in self._state["state_changelog"]:
                if entry["version"] <= target_version:
                    for key, value in entry["patch"].items():
                        if key in self._state:
                            self._state[key] = value
            
            logger.info(f"Rolled back to version {target_version}")
            
            return deepcopy(self._state)
    
    async def get_state_diff(
        self,
        from_version: int,
        to_version: int
    ) -> List[Dict[str, Any]]:
        """
        Get state changes between two versions.
        
        Args:
            from_version: Starting version
            to_version: Ending version
            
        Returns:
            List of patches applied between versions
        """
        async with self._lock:
            if self._state is None:
                return []
            
            changes = []
            for entry in self._state["state_changelog"]:
                if from_version <= entry["version"] < to_version:
                    changes.append({
                        "version": entry["version"],
                        "patch": entry["patch"],
                        "committed_by": entry["committed_by"],
                        "committed_at": entry["committed_at"]
                    })
            
            return changes
```

## LangGraph Workflow

```python
# backend/app/orchestration/workflow.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, Any, Literal
import logging

logger = logging.getLogger(__name__)

class MigrationWorkflow:
    """
    LangGraph-based workflow orchestrator with supervisor pattern.
    
    Key Features:
    - Supervisor-led routing
    - Transactional state updates
    - Checkpointing for recovery
    - Conditional transitions
    - Retry logic
    """
    
    def __init__(
        self,
        state_manager: StateManager,
        tracer: 'LangSmithTracer',
        agents: Dict[str, Any]
    ):
        self.state_manager = state_manager
        self.tracer = tracer
        self.agents = agents
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build LangGraph workflow with supervisor pattern"""
        
        # Create graph
        workflow = StateGraph(MigrationState)
        
        # ===== ADD NODES =====
        workflow.add_node("supervisor", self._supervisor_node)
        workflow.add_node("context_retrieval", self._context_retrieval_node)
        workflow.add_node("extraction", self._extraction_node)
        workflow.add_node("questionnaire", self._questionnaire_node)
        workflow.add_node("intake_draft", self._intake_draft_node)
        workflow.add_node("human_review_gate", self._human_review_gate_node)
        workflow.add_node("migration_planning", self._migration_planning_node)
        workflow.add_node("validation", self._validation_node)
        workflow.add_node("error_handler", self._error_handler_node)
        
        # ===== SET ENTRY POINT =====
        workflow.set_entry_point("supervisor")
        
        # ===== ADD CONDITIONAL EDGES FROM SUPERVISOR =====
        workflow.add_conditional_edges(
            "supervisor",
            self._route_next_node,
            {
                "context_retrieval": "context_retrieval",
                "extraction": "extraction",
                "questionnaire": "questionnaire",
                "intake_draft": "intake_draft",
                "human_review_gate": "human_review_gate",
                "migration_planning": "migration_planning",
                "validation": "validation",
                "error": "error_handler",
                "end": END
            }
        )
        
        # ===== ALL NODES RETURN TO SUPERVISOR =====
        for node in [
            "context_retrieval",
            "extraction",
            "questionnaire",
            "intake_draft",
            "human_review_gate",
            "migration_planning",
            "validation"
        ]:
            workflow.add_edge(node, "supervisor")
        
        # Error handler can retry or end
        workflow.add_conditional_edges(
            "error_handler",
            self._route_after_error,
            {
                "retry": "supervisor",
                "end": END
            }
        )
        
        # ===== ADD CHECKPOINTING =====
        memory = MemorySaver()
        compiled_graph = workflow.compile(checkpointer=memory)
        
        logger.info("LangGraph workflow compiled successfully")
        
        return compiled_graph
    
    async def _supervisor_node(self, state: MigrationState) -> MigrationState:
        """
        Supervisor node - decides next action based on current phase.
        Does NOT modify state, only routes.
        """
        await self.tracer.trace_agent(
            agent_name="supervisor",
            phase=state["phase"],
            input_data={"current_phase": state["phase"]},
            output_data={"action": "routing"},
            metadata={"state_version": state["state_version"]}
        )
        
        logger.info(f"Supervisor: Current phase = {state['phase']}, version = {state['state_version']}")
        
        return state
    
    def _route_next_node(
        self,
        state: MigrationState
    ) -> Literal[
        "context_retrieval",
        "extraction",
        "questionnaire",
        "intake_draft",
        "human_review_gate",
        "migration_planning",
        "validation",
        "error",
        "end"
    ]:
        """
        Route to next node based on current phase.
        This is the core routing logic.
        """
        phase = state["phase"]
        
        # Check for errors
        if state.get("last_error"):
            if state["retry_count"] < state["max_retries"]:
                logger.warning(f"Error detected, routing to error handler")
                return "error"
            else:
                logger.error(f"Max retries exceeded, ending workflow")
                return "end"
        
        # Phase-based routing
        if phase == WorkflowPhase.INIT:
            return "context_retrieval"
        
        elif phase == WorkflowPhase.CONTEXT_RETRIEVAL:
            return "extraction"
        
        elif phase == WorkflowPhase.EXTRACTION:
            return "questionnaire"
        
        elif phase == WorkflowPhase.QUESTIONNAIRE:
            return "intake_draft"
        
        elif phase == WorkflowPhase.INTAKE_DRAFT:
            return "human_review_gate"
        
        elif phase == WorkflowPhase.HUMAN_REVIEW:
            if state["human_reviewed"]:
                return "migration_planning"
            else:
                # Wait for human review
                return "human_review_gate"
        
        elif phase == WorkflowPhase.MIGRATION_PLANNING:
            return "validation"
        
        elif phase == WorkflowPhase.VALIDATION:
            return "end"
        
        elif phase == WorkflowPhase.COMPLETE:
            return "end"
        
        elif phase == WorkflowPhase.ERROR:
            return "error"
        
        else:
            logger.error(f"Unknown phase: {phase}")
            return "end"
    
    async def _context_retrieval_node(self, state: MigrationState) -> MigrationState:
        """Context retrieval node - delegates to agent"""
        try:
            # Read current state
            current_state = await self.state_manager.read_state()
            
            # Execute agent
            agent = self.agents["context_retrieval"]
            patch = await agent.execute(current_state)
            
            # Commit state patch
            updated_state = await self.state_manager.commit_state_patch(
                patch=patch,
                expected_version=current_state["state_version"],
                committed_by="context_retrieval_agent"
            )
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            return await self._handle_node_error(state, "context_retrieval", e)
    
    async def _extraction_node(self, state: MigrationState) -> MigrationState:
        """Extraction node - delegates to agent"""
        try:
            current_state = await self.state_manager.read_state()
            
            agent = self.agents["extraction"]
            patch = await agent.execute(current_state)
            
            updated_state = await self.state_manager.commit_state_patch(
                patch=patch,
                expected_version=current_state["state_version"],
                committed_by="extraction_agent"
            )
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return await self._handle_node_error(state, "extraction", e)
    
    async def _questionnaire_node(self, state: MigrationState) -> MigrationState:
        """Questionnaire node - delegates to agent"""
        try:
            current_state = await self.state_manager.read_state()
            
            agent = self.agents["questionnaire"]
            patch = await agent.execute(current_state)
            
            updated_state = await self.state_manager.commit_state_patch(
                patch=patch,
                expected_version=current_state["state_version"],
                committed_by="questionnaire_agent"
            )
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Questionnaire failed: {e}")
            return await self._handle_node_error(state, "questionnaire", e)
    
    async def _intake_draft_node(self, state: MigrationState) -> MigrationState:
        """Intake draft node - delegates to agent"""
        try:
            current_state = await self.state_manager.read_state()
            
            agent = self.agents["intake_draft"]
            patch = await agent.execute(current_state)
            
            updated_state = await self.state_manager.commit_state_patch(
                patch=patch,
                expected_version=current_state["state_version"],
                committed_by="intake_draft_agent"
            )
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Intake draft failed: {e}")
            return await self._handle_node_error(state, "intake_draft", e)
    
    async def _human_review_gate_node(self, state: MigrationState) -> MigrationState:
        """Human review gate - pauses workflow until review complete"""
        logger.info("Workflow paused for human review")
        
        # This node doesn't modify state, just checks if review is complete
        # The review is completed via API endpoint that updates state
        
        return state
    
    async def _migration_planning_node(self, state: MigrationState) -> MigrationState:
        """Migration planning node - delegates to agent"""
        try:
            current_state = await self.state_manager.read_state()
            
            # Verify human review completed
            if not current_state["human_reviewed"]:
                raise ValueError("Cannot proceed to planning without human review")
            
            agent = self.agents["migration_planning"]
            patch = await agent.execute(current_state)
            
            updated_state = await self.state_manager.commit_state_patch(
                patch=patch,
                expected_version=current_state["state_version"],
                committed_by="migration_planning_agent"
            )
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Migration planning failed: {e}")
            return await self._handle_node_error(state, "migration_planning", e)
    
    async def _validation_node(self, state: MigrationState) -> MigrationState:
        """Validation node - final checks"""
        try:
            current_state = await self.state_manager.read_state()
            
            agent = self.agents["validation"]
            patch = await agent.execute(current_state)
            
            # Mark as complete
            patch["phase"] = WorkflowPhase.COMPLETE
            
            updated_state = await self.state_manager.commit_state_patch(
                patch=patch,
                expected_version=current_state["state_version"],
                committed_by="validation_agent"
            )
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return await self._handle_node_error(state, "validation", e)
    
    async def _error_handler_node(self, state: MigrationState) -> MigrationState:
        """Error handler node - logs error and decides retry"""
        logger.error(f"Error handler: {state.get('last_error')}")
        
        # Increment retry count
        current_state = await self.state_manager.read_state()
        
        patch = {
            "retry_count": current_state["retry_count"] + 1,
            "error_log": current_state["error_log"] + [{
                "error": state.get("last_error"),
                "timestamp": datetime.utcnow().isoformat(),
                "phase": state["phase"]
            }]
        }
        
        updated_state = await self.state_manager.commit_state_patch(
            patch=patch,
            expected_version=current_state["state_version"],
            committed_by="error_handler"
        )
        
        return updated_state
    
    def _route_after_error(self, state: MigrationState) -> Literal["retry", "end"]:
        """Decide whether to retry or end after error"""
        if state["retry_count"] < state["max_retries"]:
            logger.info(f"Retrying (attempt {state['retry_count'] + 1}/{state['max_retries']})")
            return "retry"
        else:
            logger.error("Max retries exceeded, ending workflow")
            return "end"
    
    async def _handle_node_error(
        self,
        state: MigrationState,
        node_name: str,
        error: Exception
    ) -> MigrationState:
        """Handle error in node execution"""
        current_state = await self.state_manager.read_state()
        
        patch = {
            "last_error": f"{node_name}: {str(error)}",
            "phase": WorkflowPhase.ERROR
        }
        
        updated_state = await self.state_manager.commit_state_patch(
            patch=patch,
            expected_version=current_state["state_version"],
            committed_by=f"{node_name}_error_handler",
            validate=False  # Skip validation on error
        )
        
        return updated_state
    
    async def run(self, project_id: str) -> MigrationState:
        """
        Run complete workflow.
        
        Args:
            project_id: Project identifier
            
        Returns:
            Final state
        """
        # Initialize state
        initial_state = await self.state_manager.initialize_state(project_id)
        
        # Run graph
        config = {"configurable": {"thread_id": project_id}}
        final_state = await self.graph.ainvoke(initial_state, config)
        
        return final_state
```

## Testing Phase 3

```python
# backend/tests/test_state_manager.py
import pytest
from app.orchestration.state_manager import StateManager, StateTransactionError

@pytest.mark.asyncio
async def test_optimistic_locking():
    """Test optimistic locking prevents concurrent writes"""
    manager = StateManager()
    state = await manager.initialize_state("test-project")
    
    # First commit should succeed
    patch1 = {"phase": "context_retrieval"}
    updated1 = await manager.commit_state_patch(
        patch=patch1,
        expected_version=0,
        committed_by="agent1"
    )
    assert updated1["state_version"] == 1
    
    # Second commit with stale version should fail
    patch2 = {"phase": "extraction"}
    with pytest.raises(StateTransactionError):
        await manager.commit_state_patch(
            patch=patch2,
            expected_version=0,  # Stale version
            committed_by="agent2"
        )

@pytest.mark.asyncio
async def test_changelog_recording():
    """Test changelog records all changes"""
    manager = StateManager()
    await manager.initialize_state("test-project")
    
    # Make several commits
    for i in range(3):
        state = await manager.read_state()
        patch = {"trace_metadata": {"step": i}}
        await manager.commit_state_patch(
            patch=patch,
            expected_version=state["state_version"],
            committed_by=f"agent{i}"
        )
    
    # Check changelog
    changelog = await manager.get_changelog()
    assert len(changelog) == 3
    assert all(entry["committed_by"] == f"agent{i}" for i, entry in enumerate(changelog))
```

## Success Criteria

- [ ] State manager implements optimistic locking
- [ ] Version mismatches are detected and rejected
- [ ] Changelog records all state transitions
- [ ] LangGraph workflow routes correctly
- [ ] Checkpointing enables recovery
- [ ] LangSmith traces all operations
- [ ] Concurrent writes are prevented
- [ ] State validation catches errors
- [ ] Rollback works correctly
- [ ] All unit tests pass

## Next Steps

After Phase 3 completion, proceed to [Phase 4: Core Agents](./04-phase4-core-agents.md)