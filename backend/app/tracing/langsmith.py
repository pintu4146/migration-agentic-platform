"""
LangSmith Tracing Integration

Provides comprehensive tracing for LLM calls, agent operations, and state transitions.
"""

import os
import logging
from typing import Dict, Any, Optional
from functools import wraps
from contextlib import contextmanager

from langsmith import Client
from langsmith.run_helpers import traceable

from ..config import settings

logger = logging.getLogger(__name__)


def setup_langsmith() -> None:
    """
    Configure LangSmith tracing.
    
    Sets environment variables required for automatic tracing.
    Must be called before importing LangChain/LangGraph modules.
    """
    
    if not settings.langchain_tracing_v2:
        logger.info("LangSmith tracing disabled")
        return
    
    if not settings.langchain_api_key:
        logger.warning("LangSmith tracing enabled but LANGCHAIN_API_KEY not set")
        return
    
    # Set environment variables for LangSmith
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
    
    logger.info(f"LangSmith tracing enabled for project: {settings.langchain_project}")
    
    # Test connection
    try:
        client = Client()
        # Simple test to verify connection
        logger.info("LangSmith client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize LangSmith client: {str(e)}")


def trace_operation(
    name: str,
    run_type: str = "chain",
    tags: Optional[list[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Decorator for tracing operations in LangSmith.
    
    Args:
        name: Operation name
        run_type: Type of run (chain, llm, tool, retriever, etc.)
        tags: Optional tags for filtering
        metadata: Optional metadata
        
    Example:
        @trace_operation("extract_facts", run_type="chain", tags=["extraction"])
        async def extract_facts(state):
            ...
    """
    
    def decorator(func):
        if not settings.langchain_tracing_v2:
            # If tracing disabled, return original function
            return func
        
        @wraps(func)
        @traceable(
            name=name,
            run_type=run_type,
            tags=tags or [],
            metadata=metadata or {}
        )
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        @wraps(func)
        @traceable(
            name=name,
            run_type=run_type,
            tags=tags or [],
            metadata=metadata or {}
        )
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


@contextmanager
def trace_context(
    name: str,
    inputs: Optional[Dict[str, Any]] = None,
    tags: Optional[list[str]] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Context manager for tracing code blocks.
    
    Args:
        name: Operation name
        inputs: Input data to trace
        tags: Optional tags
        metadata: Optional metadata
        
    Example:
        with trace_context("process_documents", inputs={"doc_count": 5}):
            # Process documents
            pass
    """
    
    if not settings.langchain_tracing_v2:
        yield
        return
    
    from langsmith.run_trees import RunTree
    
    with RunTree(
        name=name,
        run_type="chain",
        inputs=inputs or {},
        tags=tags or [],
        extra=metadata or {}
    ) as run:
        try:
            yield run
        except Exception as e:
            run.end(error=str(e))
            raise


class LangSmithTracer:
    """
    Helper class for manual tracing operations.
    
    Use when decorator/context manager approach is not suitable.
    """
    
    def __init__(self):
        self.client = Client() if settings.langchain_tracing_v2 else None
        self.enabled = settings.langchain_tracing_v2
    
    async def trace_llm_call(
        self,
        provider: str,
        model: str,
        prompt: str,
        response: str,
        usage: Dict[str, int],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Trace LLM API call.
        
        Args:
            provider: Provider name (openai, gemini)
            model: Model identifier
            prompt: Input prompt
            response: Generated response
            usage: Token usage statistics
            metadata: Optional metadata
        """
        
        if not self.enabled or not self.client:
            return
        
        try:
            self.client.create_run(
                name=f"{provider}_llm_call",
                run_type="llm",
                inputs={"prompt": prompt},
                outputs={"response": response},
                extra={
                    "provider": provider,
                    "model": model,
                    "usage": usage,
                    **(metadata or {})
                }
            )
        except Exception as e:
            logger.error(f"Failed to trace LLM call: {str(e)}")
    
    async def trace_agent_execution(
        self,
        agent_name: str,
        input_state: Dict[str, Any],
        output_patch: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Trace agent execution.
        
        Args:
            agent_name: Name of the agent
            input_state: Input state snapshot
            output_patch: Output state patch
            metadata: Optional metadata
        """
        
        if not self.enabled or not self.client:
            return
        
        try:
            self.client.create_run(
                name=f"agent_{agent_name}",
                run_type="chain",
                inputs={"state_version": input_state.get("state_version")},
                outputs={"patch": output_patch},
                extra={
                    "agent": agent_name,
                    "phase": input_state.get("phase"),
                    **(metadata or {})
                }
            )
        except Exception as e:
            logger.error(f"Failed to trace agent execution: {str(e)}")
    
    async def trace_state_transition(
        self,
        from_phase: str,
        to_phase: str,
        state_version: int,
        state_diff: Dict[str, Any],
        committed_by: str
    ) -> None:
        """
        Trace state transition.
        
        Args:
            from_phase: Previous phase
            to_phase: New phase
            state_version: State version after transition
            state_diff: State changes
            committed_by: Agent that committed the change
        """
        
        if not self.enabled or not self.client:
            return
        
        try:
            self.client.create_run(
                name="state_transition",
                run_type="tool",
                inputs={
                    "from_phase": from_phase,
                    "to_phase": to_phase,
                    "version": state_version
                },
                outputs={"diff": state_diff},
                extra={
                    "committed_by": committed_by,
                    "transition": f"{from_phase} -> {to_phase}"
                }
            )
        except Exception as e:
            logger.error(f"Failed to trace state transition: {str(e)}")


# Global tracer instance
_tracer: Optional[LangSmithTracer] = None


def get_tracer() -> LangSmithTracer:
    """Get or create global tracer instance"""
    global _tracer
    
    if _tracer is None:
        _tracer = LangSmithTracer()
    
    return _tracer

# Made with Bob
