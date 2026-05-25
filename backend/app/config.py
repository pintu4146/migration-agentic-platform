"""
Configuration Management

Centralized configuration using Pydantic Settings.
Loads from environment variables with validation.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = Field(default="Migration Agent Orchestration POC", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = Field(default=True, description="Debug mode")
    
    # API
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_prefix: str = Field(default="/api", description="API prefix")
    
    # LLM Providers
    primary_provider: str = Field(default="openai", description="Primary LLM provider: openai or gemini")
    fallback_provider: str = Field(default="gemini", description="Fallback LLM provider")
    
    # OpenAI
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    openai_model: str = Field(default="gpt-4-turbo-preview", description="OpenAI model")
    openai_timeout: int = Field(default=60, description="OpenAI timeout in seconds")
    openai_max_retries: int = Field(default=3, description="OpenAI max retries")
    
    # Gemini
    gemini_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")
    gemini_model: str = Field(default="gemini-1.5-pro", description="Gemini model")
    gemini_timeout: int = Field(default=60, description="Gemini timeout in seconds")
    gemini_max_retries: int = Field(default=3, description="Gemini max retries")
    
    # LangSmith Tracing
    langchain_tracing_v2: bool = Field(default=True, description="Enable LangSmith tracing")
    langchain_api_key: Optional[str] = Field(default=None, description="LangSmith API key")
    langchain_project: str = Field(default="migration-copilot-poc", description="LangSmith project name")
    langchain_endpoint: str = Field(default="https://api.smith.langchain.com", description="LangSmith endpoint")
    
    # MCP Connector (IBM Context Studio Gateway)
    mcp_gateway_url: Optional[str] = Field(
        default=None,
        description="MCP Gateway URL (e.g., https://servicesessentials.ibm.com/mcp-gateway/...)"
    )
    mcp_gateway_token: Optional[str] = Field(default=None, description="MCP Gateway Bearer token")
    mcp_api_key: Optional[str] = Field(default=None, description="Context Studio API key (x-api-key)")
    mcp_timeout: int = Field(default=30, description="MCP timeout in seconds")
    mcp_max_retries: int = Field(default=3, description="MCP max retries")
    mcp_rate_limit_per_minute: int = Field(default=60, description="MCP rate limit per minute")
    default_context_id: str = Field(
        default="ctx_b4043773b9c6",
        description="Default Context ID (extracted from MCP_API_KEY JWT token)"
    )
    
    # Redis Cache
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    redis_db: int = Field(default=0, description="Redis database number")
    redis_ttl: int = Field(default=3600, description="Redis TTL in seconds")
    
    # Qdrant Vector Store
    qdrant_host: str = Field(default="localhost", description="Qdrant host")
    qdrant_port: int = Field(default=6333, description="Qdrant port")
    qdrant_collection: str = Field(default="migration_docs", description="Qdrant collection name")
    
    # Logging
    log_level: str = Field(default="INFO", description="Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    log_format: str = Field(default="json", description="Log format: json or text")
    
    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="CORS allowed origins"
    )
    
    # Security
    secret_key: str = Field(default="dev-secret-key-change-in-production", description="Secret key for JWT")
    
    def get_provider_config(self, provider: str) -> dict:
        """Get configuration for specific provider"""
        if provider == "openai":
            return {
                "api_key": self.openai_api_key,
                "model": self.openai_model,
                "timeout": self.openai_timeout,
                "max_retries": self.openai_max_retries
            }
        elif provider == "gemini":
            return {
                "api_key": self.gemini_api_key,
                "model": self.gemini_model,
                "timeout": self.gemini_timeout,
                "max_retries": self.gemini_max_retries
            }
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def validate_providers(self) -> bool:
        """Validate that at least one provider is configured"""
        has_openai = bool(self.openai_api_key)
        has_gemini = bool(self.gemini_api_key)
        
        if not (has_openai or has_gemini):
            raise ValueError("At least one LLM provider (OpenAI or Gemini) must be configured")
        
        return True
    
    def validate_langsmith(self) -> bool:
        """Validate LangSmith configuration"""
        if self.langchain_tracing_v2 and not self.langchain_api_key:
            raise ValueError("LangSmith tracing enabled but LANGCHAIN_API_KEY not set")
        return True


# Global settings instance
settings = Settings()

# Validate on import
settings.validate_providers()
if settings.langchain_tracing_v2:
    settings.validate_langsmith()

# Made with Bob
