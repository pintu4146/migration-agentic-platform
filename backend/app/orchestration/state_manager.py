"""
Transactional State Manager

Manages workflow state with optimistic locking and audit trail.
Follows SOLID principles with transactional guarantees.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from copy import deepcopy

from .state import (
    MigrationState,
    WorkflowPhase,
    StateChangelogEntry,
    create_initial_state,
    create_changelog_entry
)
from ..storage.redis_client import RedisClient, get_redis_client
from ..tracing.langsmith import trace_operation

logger = logging.getLogger(__name__)


class StateTransactionError(Exception):
    """Raised when state transaction fails."""
    pass


class StateValidationError(Exception):
    """Raised when state validation fails."""
    pass


class StateManager:
    """
    Transactional state manager with optimistic locking.
    
    Key Features:
    - Optimistic locking via version numbers
    - Write-ahead logging (changelog)
    - Atomic commits
    - State validation
    - Checkpoint management
    - Redis caching
    
    Design Principles:
    - SOLID: Single responsibility (state management only)
    - KISS: Simple transaction model
    - DRY: Reusable validation logic
    """
    
    def __init__(
        self,
        redis_client: Optional[RedisClient] = None,
        checkpoint_interval: int = 5
    ):
        """
        Initialize state manager.
        
        Args:
            redis_client: Redis client for caching
            checkpoint_interval: Create checkpoint every N commits
        """
        self.redis = redis_client
        self._lock = asyncio.Lock()
        self._checkpoint_interval = checkpoint_interval
        self._checkpoints: Dict[str, List[MigrationState]] = {}
    
    @trace_operation("state_init", run_type="chain", tags=["state", "init"])
    async def initialize_state(self, project_id: str) -> MigrationState:
        """
        Initialize new state for a project.
        
        Args:
            project_id: Unique project identifier
            
        Returns:
            Initialized MigrationState
        """
        async with self._lock:
            # Create initial state
            state = create_initial_state(project_id)
            
            # Save to Redis
            if self.redis:
                await self._save_to_redis(project_id, state)
            
            # Create initial checkpoint
            await self._create_checkpoint(project_id, state)
            
            logger.info(f"Initialized state for project {project_id}")
            
            return deepcopy(state)
    
    @trace_operation("state_get", run_type="chain", tags=["state", "read"])
    async def get_state(self, project_id: str) -> Optional[MigrationState]:
        """
        Get current state for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            MigrationState or None if not found
        """
        if self.redis:
            state_dict = await self.redis.get(f"state:{project_id}")
            if state_dict:
                return MigrationState(**state_dict)
        
        return None
    
    @trace_operation("state_delete", run_type="chain", tags=["state", "delete"])
    async def delete_state(self, project_id: str) -> bool:
        """
        Delete state for a project.
        
        Args:
            project_id: Project identifier
            
        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            # Check if state exists
            state = await self.get_state(project_id)
            if not state:
                logger.warning(f"No state found to delete for project {project_id}")
                return False
            
            # Delete from Redis
            if self.redis:
                await self.redis.delete(f"state:{project_id}")
            
            # Clear checkpoints
            if project_id in self._checkpoints:
                del self._checkpoints[project_id]
            
            logger.info(f"Deleted state for project {project_id}")
            return True
    
    @trace_operation("state_commit", run_type="chain", tags=["state", "write"])
    async def commit_state(
        self,
        project_id: str,
        patch: Dict[str, Any],
        expected_version: int,
        committed_by: str,
        new_phase: Optional[WorkflowPhase] = None
    ) -> MigrationState:
        """
        Commit state changes with optimistic locking.
        
        This is the core transaction method. It ensures:
        1. Only one commit at a time (via lock)
        2. Version check (optimistic locking)
        3. Atomic update
        4. Changelog recording
        5. Checkpoint creation
        
        Args:
            project_id: Project identifier
            patch: State changes to apply
            expected_version: Expected current version (for optimistic locking)
            committed_by: Agent/user making the change
            new_phase: Optional new workflow phase
            
        Returns:
            Updated MigrationState
            
        Raises:
            StateTransactionError: If version mismatch or commit fails
        """
        async with self._lock:
            # Get current state
            current_state = await self.get_state(project_id)
            if not current_state:
                raise StateTransactionError(
                    f"State not found for project {project_id}"
                )
            
            # Optimistic locking: Check version
            if current_state["state_version"] != expected_version:
                raise StateTransactionError(
                    f"Version mismatch: expected {expected_version}, "
                    f"got {current_state['state_version']}. "
                    f"State was modified by another process."
                )
            
            # Validate patch
            self._validate_patch(patch)
            
            # Apply patch
            new_state = deepcopy(current_state)
            for key, value in patch.items():
                if key in new_state:
                    new_state[key] = value
            
            # Update metadata
            new_version = current_state["state_version"] + 1
            now = datetime.utcnow().isoformat()
            
            new_state["state_version"] = new_version
            new_state["updated_at"] = now
            new_state["last_committed_by"] = committed_by
            new_state["last_committed_at"] = now
            
            # Update phase if provided
            previous_phase = current_state["phase"]
            if new_phase:
                new_state["phase"] = new_phase
            
            # Create changelog entry
            changelog_entry = create_changelog_entry(
                version=new_version,
                patch=patch,
                committed_by=committed_by,
                previous_phase=WorkflowPhase(previous_phase),
                new_phase=WorkflowPhase(new_state["phase"]),
                description=f"Commit by {committed_by}"
            )
            
            new_state["state_changelog"].append(changelog_entry)
            
            # Save to Redis
            if self.redis:
                await self._save_to_redis(project_id, new_state)
            
            # Create checkpoint if needed
            if new_version % self._checkpoint_interval == 0:
                await self._create_checkpoint(project_id, new_state)
            
            logger.info(
                f"Committed state v{new_version} for project {project_id} "
                f"by {committed_by} (phase: {previous_phase} → {new_state['phase']})"
            )
            
            return deepcopy(new_state)
    
    def _validate_patch(self, patch: Dict[str, Any]) -> None:
        """
        Validate state patch.
        
        Args:
            patch: State changes
            
        Raises:
            StateValidationError: If patch is invalid
        """
        # Don't allow direct modification of protected fields
        protected_fields = {
            "state_version",
            "created_at",
            "updated_at",
            "last_committed_by",
            "last_committed_at",
            "state_changelog"
        }
        
        for field in protected_fields:
            if field in patch:
                raise StateValidationError(
                    f"Cannot directly modify protected field: {field}"
                )
    
    async def _save_to_redis(
        self,
        project_id: str,
        state: MigrationState
    ) -> None:
        """Save state to Redis cache."""
        if self.redis:
            await self.redis.set(
                f"state:{project_id}",
                dict(state)
            )
    
    async def _create_checkpoint(
        self,
        project_id: str,
        state: MigrationState
    ) -> None:
        """
        Create state checkpoint for recovery.
        
        Args:
            project_id: Project identifier
            state: Current state
        """
        if project_id not in self._checkpoints:
            self._checkpoints[project_id] = []
        
        # Keep last 10 checkpoints
        checkpoints = self._checkpoints[project_id]
        checkpoints.append(deepcopy(state))
        if len(checkpoints) > 10:
            checkpoints.pop(0)
        
        # Update checkpoint metadata
        state["last_checkpoint_version"] = state["state_version"]
        state["checkpoint_count"] = len(checkpoints)
        
        logger.debug(
            f"Created checkpoint for project {project_id} "
            f"(version {state['state_version']})"
        )
    
    async def get_checkpoint(
        self,
        project_id: str,
        version: Optional[int] = None
    ) -> Optional[MigrationState]:
        """
        Get state checkpoint.
        
        Args:
            project_id: Project identifier
            version: Specific version (None = latest)
            
        Returns:
            MigrationState checkpoint or None
        """
        checkpoints = self._checkpoints.get(project_id, [])
        if not checkpoints:
            return None
        
        if version is None:
            return deepcopy(checkpoints[-1])
        
        for checkpoint in reversed(checkpoints):
            if checkpoint["state_version"] == version:
                return deepcopy(checkpoint)
        
        return None
    
    async def rollback(
        self,
        project_id: str,
        target_version: int
    ) -> MigrationState:
        """
        Rollback state to a previous version.
        
        Args:
            project_id: Project identifier
            target_version: Version to rollback to
            
        Returns:
            Rolled back MigrationState
            
        Raises:
            StateTransactionError: If rollback fails
        """
        async with self._lock:
            checkpoint = await self.get_checkpoint(project_id, target_version)
            if not checkpoint:
                raise StateTransactionError(
                    f"No checkpoint found for version {target_version}"
                )
            
            # Save rolled back state
            if self.redis:
                await self._save_to_redis(project_id, checkpoint)
            
            logger.warning(
                f"Rolled back project {project_id} to version {target_version}"
            )
            
            return deepcopy(checkpoint)


# Singleton instance
_state_manager: Optional[StateManager] = None


async def get_state_manager() -> StateManager:
    """
    Get or create StateManager singleton.
    
    Returns:
        StateManager instance
    """
    global _state_manager
    
    if _state_manager is None:
        redis_client = await get_redis_client()
        _state_manager = StateManager(redis_client=redis_client)
    
    return _state_manager

# Made with Bob
