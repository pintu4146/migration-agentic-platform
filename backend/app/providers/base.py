"""
Base LLM Provider Interface

Abstract base class defining the interface all LLM providers must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class ProviderResponse(BaseModel):
    """Standardized response from any LLM provider"""
    
    content: str = Field(..., description="Generated text content")
    model: str = Field(..., description="Model used for generation")
    usage: Dict[str, int] = Field(..., description="Token usage statistics")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    provider: str = Field(..., description="Provider name (openai, gemini)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "This is the generated text",
                "model": "gpt-4-turbo-preview",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150
                },
                "metadata": {"finish_reason": "stop"},
                "provider": "openai"
            }
        }


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    
    All providers must implement these methods to ensure consistent interface.
    """
    
    def __init__(self, api_key: str, model: str, timeout: int = 60, max_retries: int = 3):
        """
        Initialize provider.
        
        Args:
            api_key: API key for the provider
            model: Model identifier
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.provider_name = self.__class__.__name__.replace("Provider", "").lower()
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProviderResponse:
        """
        Generate text completion.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            metadata: Optional metadata for tracing
            
        Returns:
            ProviderResponse with generated content
        """
        pass
    
    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate structured output matching JSON schema.
        
        Args:
            prompt: User prompt
            schema: JSON schema for output validation
            system_prompt: Optional system prompt
            temperature: Sampling temperature (lower for structured output)
            metadata: Optional metadata for tracing
            
        Returns:
            Dictionary matching the provided schema
        """
        pass
    
    @abstractmethod
    async def generate_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProviderResponse:
        """
        Generate with tool/function calling capability.
        
        Args:
            prompt: User prompt
            tools: List of tool definitions
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            metadata: Optional metadata for tracing
            
        Returns:
            ProviderResponse with tool calls if applicable
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if provider is available and responding.
        
        Returns:
            True if provider is healthy, False otherwise
        """
        pass
    
    def get_provider_name(self) -> str:
        """Get provider name"""
        return self.provider_name
    
    def get_model(self) -> str:
        """Get model identifier"""
        return self.model

# Made with Bob
