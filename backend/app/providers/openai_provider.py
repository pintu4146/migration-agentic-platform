"""
OpenAI Provider Implementation

Implements the LLM provider interface for OpenAI's API.
"""

from typing import Dict, Any, List, Optional
import json
import logging
from openai import AsyncOpenAI, OpenAIError

from .base import LLMProvider, ProviderResponse

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation with GPT-4 and GPT-3.5 support"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo-preview",
        timeout: int = 60,
        max_retries: int = 3
    ):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (gpt-4-turbo-preview, gpt-3.5-turbo, etc.)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        super().__init__(api_key, model, timeout, max_retries)
        self.client = AsyncOpenAI(
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries
        )
        logger.info(f"OpenAI provider initialized with model: {model}")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProviderResponse:
        """Generate text completion using OpenAI"""
        
        try:
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Call OpenAI API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # Extract response
            content = response.choices[0].message.content or ""
            
            # Build standardized response
            return ProviderResponse(
                content=content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "response_id": response.id,
                    **(metadata or {})
                },
                provider="openai"
            )
        
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI provider: {str(e)}")
            raise
    
    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate structured JSON output using OpenAI"""
        
        try:
            # Build messages with schema instruction
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            
            # Add schema to prompt
            schema_instruction = f"\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
            messages.append({
                "role": "user",
                "content": prompt + schema_instruction
            })
            
            # Call OpenAI API with JSON mode
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=temperature
            )
            
            # Parse JSON response
            content = response.choices[0].message.content or "{}"
            result = json.loads(content)
            
            logger.info(f"Generated structured output with {response.usage.total_tokens if response.usage else 0} tokens")
            
            return result
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            raise ValueError(f"Invalid JSON response from OpenAI: {str(e)}")
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in structured generation: {str(e)}")
            raise
    
    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProviderResponse:
        """Generate with tool calling using OpenAI"""
        
        try:
            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Call OpenAI API with tools
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                temperature=temperature
            )
            
            # Extract response
            message = response.choices[0].message
            content = message.content or ""
            
            # Extract tool calls if present
            tool_calls = []
            if message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_calls.append({
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    })
            
            # Build standardized response
            return ProviderResponse(
                content=content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0
                },
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "tool_calls": tool_calls,
                    "response_id": response.id,
                    **(metadata or {})
                },
                provider="openai"
            )
        
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in tool calling: {str(e)}")
            raise
    
    async def health_check(self) -> bool:
        """Check OpenAI API health"""
        
        try:
            # Simple completion to test API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            logger.info("OpenAI health check passed")
            return True
        except Exception as e:
            logger.error(f"OpenAI health check failed: {str(e)}")
            return False

# Made with Bob
