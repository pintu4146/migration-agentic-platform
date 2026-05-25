"""
Tests for configuration management.
"""

import os
import pytest
from pydantic import ValidationError

from app.config import Settings


def test_settings_from_env():
    """Test settings loaded from environment variables"""
    # Set test environment variables
    os.environ["ENVIRONMENT"] = "test"
    os.environ["PRIMARY_PROVIDER"] = "openai"
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    settings = Settings()
    
    assert settings.environment == "test"
    assert settings.primary_provider == "openai"
    assert settings.openai_api_key == "test-key"


def test_settings_defaults():
    """Test default settings values"""
    os.environ["PRIMARY_PROVIDER"] = "openai"
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    settings = Settings()
    
    assert settings.log_level == "INFO"
    assert settings.openai_temperature == 0.7
    assert settings.openai_max_tokens == 2000
    assert settings.mcp_timeout == 30
    assert settings.mcp_retry_count == 3


def test_settings_validation_missing_provider():
    """Test validation fails when provider is not configured"""
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("GEMINI_API_KEY", None)
    os.environ["PRIMARY_PROVIDER"] = "openai"
    
    with pytest.raises(ValueError, match="PRIMARY_PROVIDER is openai but OPENAI_API_KEY is not set"):
        Settings()


def test_settings_validation_invalid_provider():
    """Test validation fails for invalid provider"""
    os.environ["PRIMARY_PROVIDER"] = "invalid"
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    with pytest.raises(ValidationError):
        Settings()


def test_settings_cors_origins_parsing():
    """Test CORS origins are parsed correctly"""
    os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:5173"
    os.environ["PRIMARY_PROVIDER"] = "openai"
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    settings = Settings()
    
    assert len(settings.cors_origins) == 2
    assert "http://localhost:3000" in settings.cors_origins
    assert "http://localhost:5173" in settings.cors_origins


def test_settings_langsmith_configuration():
    """Test LangSmith configuration"""
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = "test-langsmith-key"
    os.environ["LANGCHAIN_PROJECT"] = "test-project"
    os.environ["PRIMARY_PROVIDER"] = "openai"
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    settings = Settings()
    
    assert settings.langchain_tracing_v2 is True
    assert settings.langchain_api_key == "test-langsmith-key"
    assert settings.langchain_project == "test-project"


def test_settings_mcp_configuration():
    """Test MCP configuration"""
    os.environ["MCP_BASE_URL"] = "https://test.atlassian.net/wiki"
    os.environ["MCP_BEARER_TOKEN"] = "test-token"
    os.environ["MCP_TIMEOUT"] = "60"
    os.environ["MCP_RETRY_COUNT"] = "5"
    os.environ["PRIMARY_PROVIDER"] = "openai"
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    settings = Settings()
    
    assert settings.mcp_base_url == "https://test.atlassian.net/wiki"
    assert settings.mcp_bearer_token == "test-token"
    assert settings.mcp_timeout == 60
    assert settings.mcp_retry_count == 5


def test_settings_redis_configuration():
    """Test Redis configuration"""
    os.environ["REDIS_HOST"] = "test-redis"
    os.environ["REDIS_PORT"] = "6380"
    os.environ["REDIS_DB"] = "1"
    os.environ["REDIS_TTL"] = "7200"
    os.environ["PRIMARY_PROVIDER"] = "openai"
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    settings = Settings()
    
    assert settings.redis_host == "test-redis"
    assert settings.redis_port == 6380
    assert settings.redis_db == 1
    assert settings.redis_ttl == 7200


def test_settings_qdrant_configuration():
    """Test Qdrant configuration"""
    os.environ["QDRANT_HOST"] = "test-qdrant"
    os.environ["QDRANT_PORT"] = "6334"
    os.environ["QDRANT_COLLECTION"] = "test_collection"
    os.environ["PRIMARY_PROVIDER"] = "openai"
    os.environ["OPENAI_API_KEY"] = "test-key"
    
    settings = Settings()
    
    assert settings.qdrant_host == "test-qdrant"
    assert settings.qdrant_port == 6334
    assert settings.qdrant_collection == "test_collection"


def test_settings_fallback_provider():
    """Test fallback provider configuration"""
    os.environ["PRIMARY_PROVIDER"] = "openai"
    os.environ["FALLBACK_PROVIDER"] = "gemini"
    os.environ["OPENAI_API_KEY"] = "test-openai-key"
    os.environ["GEMINI_API_KEY"] = "test-gemini-key"
    
    settings = Settings()
    
    assert settings.primary_provider == "openai"
    assert settings.fallback_provider == "gemini"
    assert settings.openai_api_key == "test-openai-key"
    assert settings.gemini_api_key == "test-gemini-key"

# Made with Bob
