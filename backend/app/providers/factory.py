"""
Provider Factory with Automatic Fallback

Creates LLM providers with circuit breaker pattern and automatic fallback.
"""

from typing import Optional
import logging
from enum import Enum

from .base import LLMProvider
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider
from ..config import settings

logger = logging.getLogger(__name__)


class ProviderStatus(str, Enum):
    """Provider health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


class ProviderFactory:
    """
    Factory for creating LLM providers with automatic fallback.
    
    Implements circuit breaker pattern:
    - Primary provider is tried first
    - If primary fails, fallback to secondary
    - Track provider health status
    """
    
    def __init__(self):
        self.primary_provider: Optional[LLMProvider] = None
        self.fallback_provider: Optional[LLMProvider] = None
        self.primary_status = ProviderStatus.HEALTHY
        self.fallback_status = ProviderStatus.HEALTHY
        self.failure_count = 0
        self.max_failures = 3
    
    async def initialize(self) -> None:
        """Initialize providers based on configuration"""
        
        logger.info("Initializing LLM providers...")
        
        # Initialize primary provider
        try:
            self.primary_provider = self._create_provider(settings.primary_provider)
            if self.primary_provider:
                is_healthy = await self.primary_provider.health_check()
                self.primary_status = ProviderStatus.HEALTHY if is_healthy else ProviderStatus.UNAVAILABLE
                logger.info(f"Primary provider ({settings.primary_provider}): {self.primary_status}")
        except Exception as e:
            logger.error(f"Failed to initialize primary provider: {str(e)}")
            self.primary_status = ProviderStatus.UNAVAILABLE
        
        # Initialize fallback provider
        try:
            self.fallback_provider = self._create_provider(settings.fallback_provider)
            if self.fallback_provider:
                is_healthy = await self.fallback_provider.health_check()
                self.fallback_status = ProviderStatus.HEALTHY if is_healthy else ProviderStatus.UNAVAILABLE
                logger.info(f"Fallback provider ({settings.fallback_provider}): {self.fallback_status}")
            else:
                logger.warning(f"Fallback provider ({settings.fallback_provider}) was not created (likely missing API key)")
                self.fallback_status = ProviderStatus.UNAVAILABLE
        except Exception as e:
            logger.error(f"Failed to initialize fallback provider: {str(e)}", exc_info=True)
            self.fallback_status = ProviderStatus.UNAVAILABLE
        
        # Validate at least one provider is available
        if self.primary_status == ProviderStatus.UNAVAILABLE and self.fallback_status == ProviderStatus.UNAVAILABLE:
            logger.warning("No LLM providers are currently healthy, but continuing startup for POC")
            logger.warning("Document upload and workflow execution will fail until a provider is available")
            # For POC: Don't fail startup, just warn
            # raise RuntimeError("No LLM providers available")
    
    def _create_provider(self, provider_name: str) -> Optional[LLMProvider]:
        """Create provider instance"""
        
        config = settings.get_provider_config(provider_name)
        
        if not config.get("api_key"):
            logger.warning(f"No API key configured for {provider_name}")
            return None
        
        if provider_name == "openai":
            return OpenAIProvider(
                api_key=config["api_key"],
                model=config["model"],
                timeout=config["timeout"],
                max_retries=config["max_retries"]
            )
        elif provider_name == "gemini":
            return GeminiProvider(
                api_key=config["api_key"],
                model=config["model"],
                timeout=config["timeout"],
                max_retries=config["max_retries"]
            )
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
    
    async def get_provider(self, prefer_primary: bool = True) -> LLMProvider:
        """
        Get available provider with automatic fallback.
        
        Args:
            prefer_primary: Try primary provider first if True
            
        Returns:
            Available LLM provider
            
        Raises:
            RuntimeError: If no providers are available
        """
        
        # Try primary provider first if preferred and healthy
        if prefer_primary and self.primary_provider and self.primary_status == ProviderStatus.HEALTHY:
            return self.primary_provider
        
        # Try fallback provider
        if self.fallback_provider and self.fallback_status == ProviderStatus.HEALTHY:
            logger.info("Using fallback provider")
            return self.fallback_provider
        
        # Try primary even if degraded
        if self.primary_provider and self.primary_status != ProviderStatus.UNAVAILABLE:
            logger.warning("Primary provider degraded but attempting to use")
            return self.primary_provider
        
        # Last resort: try fallback even if degraded
        if self.fallback_provider and self.fallback_status != ProviderStatus.UNAVAILABLE:
            logger.warning("Fallback provider degraded but attempting to use")
            return self.fallback_provider
        
        raise RuntimeError("No LLM providers available")
    
    async def handle_provider_failure(self, provider: LLMProvider) -> None:
        """
        Handle provider failure and update status.
        
        Args:
            provider: Provider that failed
        """
        
        self.failure_count += 1
        
        # Update provider status
        if provider == self.primary_provider:
            if self.failure_count >= self.max_failures:
                self.primary_status = ProviderStatus.UNAVAILABLE
                logger.error(f"Primary provider marked as unavailable after {self.failure_count} failures")
            else:
                self.primary_status = ProviderStatus.DEGRADED
                logger.warning(f"Primary provider degraded ({self.failure_count}/{self.max_failures} failures)")
        
        elif provider == self.fallback_provider:
            if self.failure_count >= self.max_failures:
                self.fallback_status = ProviderStatus.UNAVAILABLE
                logger.error(f"Fallback provider marked as unavailable after {self.failure_count} failures")
            else:
                self.fallback_status = ProviderStatus.DEGRADED
                logger.warning(f"Fallback provider degraded ({self.failure_count}/{self.max_failures} failures)")
    
    async def handle_provider_success(self, provider: LLMProvider) -> None:
        """
        Handle provider success and reset failure count.
        
        Args:
            provider: Provider that succeeded
        """
        
        # Reset failure count on success
        if self.failure_count > 0:
            logger.info(f"Provider recovered, resetting failure count from {self.failure_count}")
            self.failure_count = 0
        
        # Update provider status to healthy
        if provider == self.primary_provider:
            self.primary_status = ProviderStatus.HEALTHY
        elif provider == self.fallback_provider:
            self.fallback_status = ProviderStatus.HEALTHY
    
    def get_status(self) -> dict:
        """Get current provider status"""
        return {
            "primary": {
                "provider": settings.primary_provider,
                "status": self.primary_status,
                "available": self.primary_provider is not None
            },
            "fallback": {
                "provider": settings.fallback_provider,
                "status": self.fallback_status,
                "available": self.fallback_provider is not None
            },
            "failure_count": self.failure_count
        }


# Global factory instance
_factory: Optional[ProviderFactory] = None


async def get_provider_factory() -> ProviderFactory:
    """Get or create global provider factory"""
    global _factory
    
    if _factory is None:
        _factory = ProviderFactory()
        await _factory.initialize()
    
    return _factory


async def get_provider(prefer_primary: bool = True) -> LLMProvider:
    """
    Convenience function to get provider.
    
    Args:
        prefer_primary: Try primary provider first if True
        
    Returns:
        Available LLM provider
    """
    factory = await get_provider_factory()
    return await factory.get_provider(prefer_primary)

# Made with Bob
