"""
Command Generator

LLM-powered diagnostic command generator for the Advanced Assistance service.
Given a question and the reason more context is needed, it produces a targeted
PowerShell, Bash, Maven, Gradle, or Docker command that a user can run locally
and paste the output back into the chat.
"""

import json
import logging
import re
from datetime import datetime
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ── Output model ─────────────────────────────────────────────────────────────

class DiagnosticCommand(BaseModel):
    """
    A diagnostic command suggested by the assistant.

    Attributes:
        shell: Shell type — 'powershell', 'bash', 'maven', 'gradle', 'docker', 'other'
        command: The exact command string to run.
        purpose: One-sentence explanation of what this command reveals.
        expected_output: Brief description of what useful information to look for.
        generated_at: ISO timestamp of generation.
    """

    shell: str = Field(description="Shell type: powershell|bash|maven|gradle|docker|other")
    command: str = Field(description="The exact runnable command string")
    purpose: str = Field(description="One-sentence explanation of what this reveals")
    expected_output: str = Field(description="What to look for in the output")
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ── System prompt ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a senior cloud migration architect assistant.

Your task is to generate a single, precise diagnostic command that a developer can run
on their local machine or build system to retrieve the missing context needed to answer
the migration question.

Rules:
- Return ONLY valid JSON — no markdown fences, no explanation outside the JSON.
- The command must be safe to run (no destructive operations: no rm -rf, no DROP TABLE, etc.)
- Prefer commands that produce compact, machine-readable output
- Choose the appropriate shell for the technology (Maven project → mvn, .NET → PowerShell, etc.)
- The command string must be copy-pasteable with no placeholders

JSON schema (return exactly this structure):
{
  "shell": "<powershell|bash|maven|gradle|docker|other>",
  "command": "<exact runnable command>",
  "purpose": "<one sentence: what migration fact this reveals>",
  "expected_output": "<what to look for in the output>"
}
"""

_STRIP_MD = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _strip_markdown(text: str) -> str:
    """Remove markdown code fences that Gemini/GPT-4 sometimes wrap JSON in."""
    return _STRIP_MD.sub("", text).strip()


# ── Generator class ───────────────────────────────────────────────────────────

class CommandGenerator:
    """
    Generates diagnostic commands using an LLM.

    Responsibilities:
    - Accept a natural-language question + reason for missing context
    - Produce a DiagnosticCommand via LLM
    - Strip markdown from LLM response before JSON parsing (CRITICAL_BUGS_MEMORY rule #4)
    - Fall back gracefully if LLM is unavailable

    Design:
    - Own LLM instance — never imports from backend/app/
    - Supports OpenAI (primary) and Google Gemini (fallback)
    - MOCK_MODE constant for testing without LLM credits
    """

    MOCK_MODE: bool = False  # Set True in tests

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        model: str = "gpt-4-turbo-preview",
    ):
        """
        Initialise the generator.

        Args:
            openai_api_key: OpenAI API key. Falls back to OPENAI_API_KEY env var.
            gemini_api_key: Google Gemini API key. Falls back to GEMINI_API_KEY env var.
            model: Primary LLM model name.
        """
        self._openai_key = openai_api_key
        self._gemini_key = gemini_api_key
        self._model = model
        self._llm: Optional[ChatOpenAI | ChatGoogleGenerativeAI] = None

    def _get_llm(self) -> ChatOpenAI | ChatGoogleGenerativeAI:
        """Lazy-initialise LLM client with OpenAI primary / Gemini fallback."""
        if self._llm is not None:
            return self._llm

        if self._openai_key or _env("OPENAI_API_KEY"):
            self._llm = ChatOpenAI(
                model=self._model,
                temperature=0.2,
                api_key=self._openai_key or _env("OPENAI_API_KEY"),
            )
            logger.info("CommandGenerator: using OpenAI %s", self._model)
        elif self._gemini_key or _env("GEMINI_API_KEY"):
            self._llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-pro",
                temperature=0.2,
                google_api_key=self._gemini_key or _env("GEMINI_API_KEY"),
            )
            logger.info("CommandGenerator: using Gemini fallback")
        else:
            raise RuntimeError(
                "CommandGenerator: no LLM API key available. "
                "Set OPENAI_API_KEY or GEMINI_API_KEY."
            )
        return self._llm

    async def generate(
        self,
        question: str,
        reason: str,
        tech_context: Optional[str] = None,
    ) -> DiagnosticCommand:
        """
        Generate a diagnostic command for the given question.

        Args:
            question: The migration question that needs more context.
            reason: Why the current state data is insufficient.
            tech_context: Optional technology hints (e.g. 'Java 11, Maven, Spring Boot').

        Returns:
            DiagnosticCommand with shell, command, purpose, expected_output.
        """
        if self.MOCK_MODE:
            return DiagnosticCommand(
                shell="maven",
                command="mvn dependency:tree -Dverbose",
                purpose="Lists all transitive Maven dependencies and their versions.",
                expected_output="Look for security-related deps (spring-security, shiro) and their versions.",
            )

        context_hint = f"\nTechnology context: {tech_context}" if tech_context else ""
        user_prompt = (
            f"Migration question: {question}\n"
            f"Why current data is insufficient: {reason}"
            f"{context_hint}\n\n"
            "Generate the single most useful diagnostic command."
        )

        llm = self._get_llm()
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = await llm.ainvoke(messages)
            raw = response.content
            cleaned = _strip_markdown(raw)  # CRITICAL: strip before json.loads
            data = json.loads(cleaned)

            cmd = DiagnosticCommand(
                shell=data.get("shell", "bash"),
                command=data["command"],
                purpose=data.get("purpose", ""),
                expected_output=data.get("expected_output", ""),
            )
            logger.info(
                "CommandGenerator: generated %s command for '%s'",
                cmd.shell,
                question[:60],
            )
            return cmd

        except json.JSONDecodeError as exc:
            logger.error("CommandGenerator: JSON parse failed — %s\nRaw: %s", exc, raw)
            # Return a safe fallback
            return DiagnosticCommand(
                shell="bash",
                command=f"# Could not generate command: {exc}",
                purpose="LLM response was not valid JSON.",
                expected_output="N/A",
            )
        except Exception as exc:
            logger.error("CommandGenerator: LLM call failed — %s", exc)
            raise


# ── Module helpers ────────────────────────────────────────────────────────────

def _env(key: str) -> Optional[str]:
    """Read an environment variable, return None if absent."""
    import os
    return os.environ.get(key)


# Module-level singleton
_generator: Optional[CommandGenerator] = None


def get_command_generator(
    openai_api_key: Optional[str] = None,
    gemini_api_key: Optional[str] = None,
) -> CommandGenerator:
    """Return the module-level CommandGenerator singleton."""
    global _generator
    if _generator is None:
        _generator = CommandGenerator(
            openai_api_key=openai_api_key,
            gemini_api_key=gemini_api_key,
        )
    return _generator

# Made with Bob
