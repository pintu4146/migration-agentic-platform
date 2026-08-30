"""
ReAct Agent — SWAP POINT

This is the ONLY file that changes when upgrading from LangChain AgentExecutor
to LangGraph ToolNode. All tool functions, prompts, and API endpoints remain
unchanged.

Current implementation:  LangChain AgentExecutor + create_react_agent
Future swap target:       LangGraph ToolNode (see SWAP POINT comment below)

See: docs/ADVANCED_ASSISTANCE_PLAN.md — Sub-Task 4
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from .prompts import REACT_SYSTEM_PROMPT, format_history_for_prompt
from .tools import V1_TOOLS, V2_STUBS, ALL_TOOLS
from .conversation_store import get_conversation_store

logger = logging.getLogger(__name__)

# ── Agent config ──────────────────────────────────────────────────────────────
MAX_ITERATIONS = 8
HANDLE_PARSING_ERRORS = True  # CRITICAL: prevents hard crash on malformed LLM output

# ── ReAct prompt template ────────────────────────────────────────────────────
# LangChain ReAct agents require the exact variable names:
# {tools}, {tool_names}, {input}, {agent_scratchpad}
_REACT_PROMPT_TEMPLATE = (
    REACT_SYSTEM_PROMPT
    + """

{history}

Available tools:
{tools}

Tool names: {tool_names}

Use the following format exactly:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat up to {max_iterations} times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""
)


def _build_llm(
    openai_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
    model: str = "gpt-4-turbo-preview",
) -> ChatOpenAI | ChatGoogleGenerativeAI:
    """Build LLM instance — OpenAI primary, Gemini fallback."""
    import os

    oai_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
    gem_key = gemini_api_key or os.environ.get("GEMINI_API_KEY")

    if oai_key:
        logger.info("ReActAgent: using OpenAI %s", model)
        return ChatOpenAI(
            model=model,
            temperature=0.1,
            api_key=oai_key,
            streaming=True,
        )
    elif gem_key:
        logger.info("ReActAgent: using Gemini fallback")
        return ChatGoogleGenerativeAI(
            model="gemini-1.5-pro",
            temperature=0.1,
            google_api_key=gem_key,
            streaming=True,
        )
    else:
        raise RuntimeError(
            "ReActAgent: no LLM API key found. Set OPENAI_API_KEY or GEMINI_API_KEY."
        )


# ══════════════════════════════════════════════════════════════════════════════
# CURRENT IMPLEMENTATION: LangChain AgentExecutor
# ══════════════════════════════════════════════════════════════════════════════

class ReActAgent:
    """
    ReAct conversational agent for the Advanced Assistance service.

    Wraps LangChain AgentExecutor with:
    - Full tool registry (V1 implemented + V2 stubs)
    - Per-project conversation history via ConversationStore
    - Streaming SSE output (yields chunks as they arrive)
    - handle_parsing_errors=True (CRITICAL_BUGS_MEMORY rule compliance)
    - max_iterations cap to prevent runaway loops

    Streaming note:
    LangChain AgentExecutor does not support true token-level streaming for
    ReAct agents in v0.1.x. We stream the final answer and emit intermediate
    Thought/Action/Observation steps as discrete SSE events.
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        model: str = "gpt-4-turbo-preview",
    ):
        self._openai_key = openai_api_key
        self._gemini_key = gemini_api_key
        self._model = model
        self._executor: Optional[AgentExecutor] = None

    def _get_executor(self) -> AgentExecutor:
        """Lazy-build and cache the AgentExecutor."""
        if self._executor is not None:
            return self._executor

        llm = _build_llm(self._openai_key, self._gemini_key, self._model)

        prompt = PromptTemplate.from_template(_REACT_PROMPT_TEMPLATE)
        # Inject max_iterations into prompt as a static partial
        prompt = prompt.partial(max_iterations=str(MAX_ITERATIONS))

        agent = create_react_agent(llm=llm, tools=ALL_TOOLS, prompt=prompt)

        self._executor = AgentExecutor(
            agent=agent,
            tools=ALL_TOOLS,
            verbose=True,
            max_iterations=MAX_ITERATIONS,
            handle_parsing_errors=HANDLE_PARSING_ERRORS,  # CRITICAL
            return_intermediate_steps=True,
        )
        logger.info(
            "ReActAgent: AgentExecutor built with %d tools (V1=%d, V2_stubs=%d)",
            len(ALL_TOOLS),
            len(V1_TOOLS),
            len(V2_STUBS),
        )
        return self._executor

    async def stream_response(
        self,
        project_id: str,
        user_message: str,
    ) -> AsyncGenerator[str, None]:
        """
        Run the ReAct agent and stream SSE events back to the caller.

        Yields SSE-formatted strings:
          - event: thought     (intermediate Thought steps)
          - event: action      (tool call + input)
          - event: observation (tool result)
          - event: answer      (final answer, streamed word-by-word)
          - event: error       (on failure)
          - event: done        (signals end of stream)

        Args:
            project_id: Project identifier (for history + tool context).
            user_message: The user's question.

        Yields:
            SSE-formatted string chunks.
        """
        store = get_conversation_store()

        # Persist user message
        await store.append(project_id=project_id, role="user", content=user_message)

        # Load history for context
        history = await store.get_history(project_id=project_id, last_n=20)
        history_text = format_history_for_prompt(history[:-1])  # exclude current msg

        executor = self._get_executor()

        # We inject project_id into the question so tools can use it
        enriched_input = f"[project_id={project_id}] {user_message}"

        try:
            # ── Run synchronously in thread pool to avoid blocking event loop ──
            loop = asyncio.get_event_loop()
            result: Dict[str, Any] = await loop.run_in_executor(
                None,
                lambda: executor.invoke(
                    {
                        "input": enriched_input,
                        "history": history_text,
                    }
                ),
            )

            # ── Stream intermediate steps ────────────────────────────────────
            intermediate = result.get("intermediate_steps", [])
            for action, observation in intermediate:
                # Emit Thought (stored inside action.log)
                thought_text = _extract_thought(action.log)
                if thought_text:
                    yield _sse("thought", {"text": thought_text})

                # Emit Action
                yield _sse(
                    "action",
                    {
                        "tool": action.tool,
                        "input": str(action.tool_input)[:500],
                    },
                )

                # Emit Observation
                yield _sse(
                    "observation",
                    {"text": str(observation)[:1000]},
                )

            # ── Stream final answer word-by-word ─────────────────────────────
            final_answer: str = result.get("output", "")
            words = final_answer.split()
            buffer = []
            for i, word in enumerate(words):
                buffer.append(word)
                # Emit every 8 words for a smooth streaming feel
                if len(buffer) >= 8 or i == len(words) - 1:
                    yield _sse("answer", {"text": " ".join(buffer) + " "})
                    buffer = []
                    await asyncio.sleep(0.02)  # yield control to event loop

            # ── Persist assistant reply ──────────────────────────────────────
            metadata = {
                "steps": len(intermediate),
                "tools_used": [a.tool for a, _ in intermediate],
            }
            await store.append(
                project_id=project_id,
                role="assistant",
                content=final_answer,
                metadata=metadata,
            )

            yield _sse("done", {"project_id": project_id})

        except Exception as exc:
            logger.error(
                "ReActAgent: stream_response failed for project %s — %s",
                project_id,
                exc,
                exc_info=True,
            )
            yield _sse("error", {"message": str(exc)})
            yield _sse("done", {"project_id": project_id})


# ══════════════════════════════════════════════════════════════════════════════
# ── SWAP POINT ────────────────────────────────────────────────────────────────
#
# To upgrade to LangGraph ToolNode, replace ReActAgent._get_executor() with:
#
#   from langgraph.prebuilt import create_react_agent as lg_react_agent
#   from langgraph.prebuilt import ToolNode
#
#   def _get_graph(self):
#       if self._graph is not None:
#           return self._graph
#       llm = _build_llm(...)
#       llm_with_tools = llm.bind_tools(ALL_TOOLS)
#       tool_node = ToolNode(ALL_TOOLS)
#       self._graph = lg_react_agent(llm_with_tools, tools=ALL_TOOLS)
#       return self._graph
#
# And replace executor.invoke(...) in stream_response with:
#   async for chunk in self._get_graph().astream({"messages": [...]})
#
# ALL other files (tools.py, prompts.py, api/chat.py, frontend) stay unchanged.
# ── END SWAP POINT ────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sse(event: str, data: Dict[str, Any]) -> str:
    """Format a single SSE message."""
    payload = json.dumps(data)
    return f"event: {event}\ndata: {payload}\n\n"


def _extract_thought(log: str) -> str:
    """Extract the Thought text from an action's log string."""
    if not log:
        return ""
    # LangChain logs start with "Thought: ..." or just the thought text
    lines = log.strip().splitlines()
    thought_lines = []
    for line in lines:
        if line.startswith("Action:"):
            break
        line = line.removeprefix("Thought:").strip()
        if line:
            thought_lines.append(line)
    return " ".join(thought_lines)


# Module-level singleton
_agent: Optional[ReActAgent] = None


def get_react_agent(
    openai_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
) -> ReActAgent:
    """Return the module-level ReActAgent singleton."""
    global _agent
    if _agent is None:
        _agent = ReActAgent(
            openai_api_key=openai_api_key,
            gemini_api_key=gemini_api_key,
        )
    return _agent

# Made with Bob
