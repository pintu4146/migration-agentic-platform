"""
Google Gemini Provider Implementation

Implements the LLM provider interface for Google's Gemini API.
"""

from typing import Dict, Any, List, Optional
import json
import logging
import google.generativeai as genai
from google.generativeai.types import GenerationConfig

from .base import LLMProvider, ProviderResponse

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    """Google Gemini provider implementation"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-1.5-pro",
        timeout: int = 60,
        max_retries: int = 3
    ):
        """
        Initialize Gemini provider.
        
        Args:
            api_key: Google API key
            model: Model to use (gemini-1.5-pro, gemini-pro, etc.)
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        super().__init__(api_key, model, timeout, max_retries)
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model)
        
        logger.info(f"Gemini provider initialized with model: {model}")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProviderResponse:
        """Generate text completion using Gemini"""
        
        try:
            # Combine system prompt and user prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            # Configure generation
            generation_config = GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
            
            # Generate response
            response = await self.client.generate_content_async(
                full_prompt,
                generation_config=generation_config
            )
            
            # Extract content
            content = response.text if response.text else ""
            
            # Build standardized response
            return ProviderResponse(
                content=content,
                model=self.model,
                usage={
                    "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0,
                    "total_tokens": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0
                },
                metadata={
                    "finish_reason": response.candidates[0].finish_reason.name if response.candidates else "unknown",
                    **(metadata or {})
                },
                provider="gemini"
            )
        
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            raise
    
    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate structured JSON output using Gemini"""
        
        try:
            # Build prompt with schema instruction
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            schema_instruction = f"\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
            full_prompt += schema_instruction
            
            # Configure generation
            generation_config = GenerationConfig(
                temperature=temperature,
                response_mime_type="application/json"
            )
            
            # Generate response
            response = await self.client.generate_content_async(
                full_prompt,
                generation_config=generation_config
            )
            
            # Parse JSON response
            content = response.text if response.text else "{}"
            result = json.loads(content)
            
            logger.info(f"Generated structured output with Gemini")
            
            return result
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            raise ValueError(f"Invalid JSON response from Gemini: {str(e)}")
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            raise
    
    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProviderResponse:
        """Generate with tool calling using Gemini"""
        
        try:
            # Build full prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            # Configure generation
            generation_config = GenerationConfig(
                temperature=temperature
            )
            
            # Convert tools to Gemini format
            gemini_tools = self._convert_tools_to_gemini_format(tools)
            
            # Generate response with tools
            response = await self.client.generate_content_async(
                full_prompt,
                generation_config=generation_config,
                tools=gemini_tools
            )
            
            # Extract content
            content = response.text if response.text else ""
            
            # Extract function calls if present
            tool_calls = []
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call'):
                        tool_calls.append({
                            "type": "function",
                            "function": {
                                "name": part.function_call.name,
                                "arguments": json.dumps(dict(part.function_call.args))
                            }
                        })
            
            # Build standardized response
            return ProviderResponse(
                content=content,
                model=self.model,
                usage={
                    "prompt_tokens": response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else 0,
                    "completion_tokens": response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else 0,
                    "total_tokens": response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else 0
                },
                metadata={
                    "finish_reason": response.candidates[0].finish_reason.name if response.candidates else "unknown",
                    "tool_calls": tool_calls,
                    **(metadata or {})
                },
                provider="gemini"
            )
        
        except Exception as e:
            logger.error(f"Gemini tool calling error: {str(e)}")
            raise
    
    async def health_check(self) -> bool:
        """Check Gemini API health"""
        
        try:
            # Simple generation to test API
            response = await self.client.generate_content_async(
                "test",
                generation_config=GenerationConfig(max_output_tokens=5)
            )
            logger.info("Gemini health check passed")
            return True
        except Exception as e:
            logger.error(f"Gemini health check failed: {str(e)}")
            return False
    
    def _convert_tools_to_gemini_format(self, tools: List[Dict[str, Any]]) -> List[Any]:
        """Convert OpenAI-style tools to Gemini format"""
        
        gemini_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                function = tool.get("function", {})
                gemini_tools.append({
                    "name": function.get("name"),
                    "description": function.get("description"),
                    "parameters": function.get("parameters", {})
                })
        
        return gemini_tools

# Made with Bob
