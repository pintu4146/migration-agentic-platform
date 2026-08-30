# watsonx Provider Enhancement Plan

**Feature**: Add IBM watsonx.ai as a first-class LLM provider in the Migration Copilot.  
**Status**: Planned enhancement — architecture is fully ready; implementation is the next provider addition.  
**Priority**: High — strategic alignment with IBM's own AI platform for client demos.

---

## Why watsonx

The Migration Copilot already supports OpenAI (primary) and Google Gemini (fallback) through a
`LLMProvider` abstract base class. Adding watsonx.ai requires implementing the same four-method
interface in a new `WatsonXProvider` class and registering it in `ProviderFactory` — no changes
to any agent, orchestration, or state management code.

This makes the system:
- **Demo-aligned**: IBM clients see IBM's own foundation models driving the migration analysis
- **Roster-complete**: `PRIMARY_PROVIDER=watsonx` routes all LLM calls through watsonx.ai
- **Fallback-safe**: existing circuit-breaker automatically falls back to Gemini if watsonx is
  unavailable — zero code change required

---

## Interface Contract (Unchanged)

Every provider must implement `backend/app/providers/base.py`:

```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt, system_prompt, temperature, max_tokens, metadata) -> ProviderResponse:
        """Open-ended text generation"""

    @abstractmethod
    async def generate_structured(self, prompt, schema, system_prompt, temperature, metadata) -> Dict:
        """JSON-schema-constrained output — primary call pattern for all agents"""

    @abstractmethod
    async def generate_with_tools(self, prompt, tools, system_prompt, temperature, metadata) -> ProviderResponse:
        """Function/tool calling capability"""

    @abstractmethod
    async def health_check(self) -> bool:
        """Liveness check used by ProviderFactory circuit breaker"""
```

---

## New File: `backend/app/providers/watsonx_provider.py`

```python
"""
IBM watsonx.ai Provider Implementation

Implements the LLMProvider interface for IBM watsonx.ai.
Supported models: ibm/granite-13b-instruct-v2, meta-llama/llama-3-70b-instruct,
                  mistralai/mistral-large, ibm/granite-34b-code-instruct-v2
"""

from typing import Dict, Any, List, Optional
import json
import logging
from ibm_watsonx_ai.foundation_models import ModelInference
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

from .base import LLMProvider, ProviderResponse

logger = logging.getLogger(__name__)


class WatsonXProvider(LLMProvider):
    """IBM watsonx.ai provider — implements LLMProvider ABC"""

    def __init__(
        self,
        api_key: str,
        project_id: str,
        model: str = "ibm/granite-13b-instruct-v2",
        url: str = "https://us-south.ml.cloud.ibm.com",
        timeout: int = 120,
        max_retries: int = 3
    ):
        super().__init__(api_key, model, timeout, max_retries)
        self.project_id = project_id

        credentials = {
            "apikey": api_key,
            "url": url
        }
        self.client = ModelInference(
            model_id=model,
            credentials=credentials,
            project_id=project_id,
            params={
                GenParams.DECODING_METHOD: "greedy",
                GenParams.MAX_NEW_TOKENS: 2000,
                GenParams.STOP_SEQUENCES: []
            }
        )
        logger.info(f"WatsonX provider initialized with model: {model}")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProviderResponse:
        """Generate text using watsonx.ai"""
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        response = self.client.generate(
            prompt=full_prompt,
            params={
                GenParams.MAX_NEW_TOKENS: max_tokens,
                GenParams.TEMPERATURE: temperature
            }
        )

        content = response["results"][0]["generated_text"]
        tokens = response["results"][0].get("generated_token_count", 0)

        return ProviderResponse(
            content=content,
            model=self.model,
            usage={"prompt_tokens": 0, "completion_tokens": tokens, "total_tokens": tokens},
            metadata={"finish_reason": response["results"][0].get("stop_reason", "stop"),
                      **(metadata or {})},
            provider="watsonx"
        )

    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate structured JSON output.

        IMPORTANT: watsonx Granite models, like Gemini, sometimes wrap JSON output
        in markdown code fences. Strip them before json.loads() — same pattern as
        GeminiProvider.generate_structured() in gemini_provider.py.
        """
        schema_instruction = (
            f"\n\nRespond ONLY with valid JSON matching this schema:\n"
            f"{json.dumps(schema, indent=2)}\n\nDo not include any text outside the JSON."
        )
        full_prompt = (
            f"{system_prompt}\n\n{prompt}{schema_instruction}"
            if system_prompt
            else f"{prompt}{schema_instruction}"
        )

        response = self.client.generate(
            prompt=full_prompt,
            params={GenParams.MAX_NEW_TOKENS: 3000, GenParams.TEMPERATURE: temperature}
        )

        content = response["results"][0]["generated_text"].strip()

        # Strip markdown fences — Granite models wrap output in ```json ... ```
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        return json.loads(content.strip())

    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProviderResponse:
        """
        Tool calling via prompt engineering.
        Granite 34B Code and Llama 3 support native function calling;
        other models fall back to JSON-in-prompt approach.
        """
        tools_description = json.dumps(tools, indent=2)
        tool_prompt = (
            f"{prompt}\n\nAvailable tools:\n{tools_description}\n\n"
            "If you need to call a tool, respond with JSON: "
            '{"tool": "<name>", "arguments": {...}}'
        )
        return await self.generate(tool_prompt, system_prompt, temperature, 2000, metadata)

    async def health_check(self) -> bool:
        """Ping watsonx.ai with a minimal generation call"""
        try:
            response = self.client.generate(
                prompt="ping",
                params={GenParams.MAX_NEW_TOKENS: 5}
            )
            logger.info("WatsonX health check passed")
            return bool(response.get("results"))
        except Exception as e:
            logger.error(f"WatsonX health check failed: {str(e)}")
            return False

# Made with Bob
```

---

## Changes to Existing Files (Surgical — 3 Files Only)

### 1. `backend/app/config.py` — Add watsonx settings block

```python
# watsonx.ai Configuration
watsonx_api_key: Optional[str] = Field(default=None, description="IBM watsonx.ai API key")
watsonx_project_id: Optional[str] = Field(default=None, description="IBM watsonx project ID")
watsonx_url: str = Field(
    default="https://us-south.ml.cloud.ibm.com",
    description="watsonx.ai regional endpoint"
)
watsonx_model: str = Field(
    default="ibm/granite-13b-instruct-v2",
    description="watsonx model ID"
)
watsonx_timeout: int = Field(default=120, description="watsonx timeout in seconds")
watsonx_max_retries: int = Field(default=3, description="watsonx max retries")
```

Also update `get_provider_config()` and `validate_providers()` to include `"watsonx"`.

### 2. `backend/app/providers/factory.py` — Register watsonx in `_create_provider()`

```python
elif provider_name == "watsonx":
    from .watsonx_provider import WatsonXProvider
    return WatsonXProvider(
        api_key=config["api_key"],
        project_id=config["project_id"],
        model=config["model"],
        url=config.get("url", "https://us-south.ml.cloud.ibm.com"),
        timeout=config["timeout"],
        max_retries=config["max_retries"]
    )
```

### 3. `.env.example` — Add watsonx env vars

```bash
# ============================================================================
# IBM watsonx.ai Configuration (optional — set PRIMARY_PROVIDER=watsonx to use)
# ============================================================================
WATSONX_API_KEY=your-ibm-cloud-api-key-here
WATSONX_PROJECT_ID=your-watsonx-project-id-here
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL=ibm/granite-13b-instruct-v2

# To use watsonx as primary:
# PRIMARY_PROVIDER=watsonx
# FALLBACK_PROVIDER=gemini
```

---

## Supported Models

| Model ID | Best Use | Notes |
|----------|----------|-------|
| `ibm/granite-13b-instruct-v2` | Fact extraction, structured output | Default; strong instruction following |
| `ibm/granite-34b-code-instruct-v2` | Command generation in Advanced Assistance | Best for diagnostic command generation |
| `meta-llama/llama-3-70b-instruct` | Intake drafting, migration planning | Highest quality for long-form generation |
| `mistralai/mistral-large` | Questionnaire generation | Strong reasoning for gap analysis |

---

## Critical Implementation Notes

### JSON Fence Stripping (Mandatory)
Granite models wrap structured responses in markdown fences exactly like Gemini.
The `generate_structured()` method already strips them — same pattern as
`backend/app/providers/gemini_provider.py` lines 178–187. Do not skip this.

### `ibm-watsonx-ai` is Synchronous
The `ibm-watsonx-ai` SDK's `ModelInference.generate()` is **not async-native**.
Wrap blocking calls with `asyncio.get_event_loop().run_in_executor()` for production
to avoid blocking the FastAPI event loop:

```python
import asyncio

loop = asyncio.get_event_loop()
response = await loop.run_in_executor(
    None,
    lambda: self.client.generate(prompt=full_prompt, params=params)
)
```

### Config Validates on Import
`backend/app/config.py` calls `validate_providers()` at module load. Update the
validator to accept `"watsonx"` as a valid provider string or it will raise
`ValueError` when `PRIMARY_PROVIDER=watsonx` is set, even before the app starts.

---

## Required Package

```bash
pip install ibm-watsonx-ai>=0.2.6
```

Add to `backend/requirements.txt`:
```
ibm-watsonx-ai==0.2.6
```

---

## Testing

```bash
cd backend
pytest tests/test_watsonx_provider.py -v -m unit

# Integration test (requires live watsonx credentials)
pytest tests/test_watsonx_provider.py -v -m integration
```

Key test cases:
1. `test_generate_returns_provider_response` — validates `ProviderResponse` schema
2. `test_generate_structured_strips_fences` — verifies markdown fence stripping
3. `test_health_check_returns_bool` — circuit breaker compatibility
4. `test_factory_creates_watsonx_when_configured` — ProviderFactory registration
5. `test_fallback_to_gemini_on_watsonx_failure` — circuit breaker fallback path

---

## Activation (One Line)

Once implemented, switch the entire Migration Copilot to watsonx.ai by setting one
environment variable:

```bash
PRIMARY_PROVIDER=watsonx
```

All 5 agents (Context Retrieval, Extraction, Questionnaire, Intake Draft,
Review/Validation) immediately route their LLM calls through watsonx.ai — zero
changes to agent code, orchestration, state management, or the frontend.

# Made with Bob
