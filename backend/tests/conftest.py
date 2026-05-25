"""
Pytest configuration and fixtures for testing.
"""

import os
import pytest
from typing import Generator
from unittest.mock import Mock, AsyncMock

# Set test environment variables before importing app modules
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["PRIMARY_PROVIDER"] = "openai"
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["OPENAI_MODEL"] = "gpt-4"
os.environ["LANGCHAIN_TRACING_V2"] = "false"


@pytest.fixture
def mock_openai_client() -> Mock:
    """Mock OpenAI client"""
    client = Mock()
    
    # Mock chat completion
    completion = Mock()
    completion.choices = [Mock(message=Mock(content="Test response"))]
    completion.usage = Mock(
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30
    )
    
    client.chat.completions.create = AsyncMock(return_value=completion)
    
    return client


@pytest.fixture
def mock_gemini_client() -> Mock:
    """Mock Gemini client"""
    client = Mock()
    
    # Mock generate content
    response = Mock()
    response.text = "Test response"
    response.usage_metadata = Mock(
        prompt_token_count=10,
        candidates_token_count=20,
        total_token_count=30
    )
    
    model = Mock()
    model.generate_content = AsyncMock(return_value=response)
    client.GenerativeModel = Mock(return_value=model)
    
    return client


@pytest.fixture
def sample_provider_response() -> dict:
    """Sample provider response"""
    return {
        "content": "Test response content",
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30
        },
        "model": "gpt-4",
        "finish_reason": "stop"
    }


@pytest.fixture
def sample_migration_state() -> dict:
    """Sample migration workflow state"""
    return {
        "project_id": "test_project_123",
        "state_version": 1,
        "phase": "init",
        "mcp_request_profile": {},
        "context_pack": {},
        "normalized_docs": [],
        "extracted_facts": {},
        "missing_questions": [],
        "intake_draft": {},
        "human_reviewed": False,
        "migration_plan": {},
        "validation_results": {},
        "review_flags": [],
        "trace_metadata": {},
        "last_committed_by": "test",
        "last_committed_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_mcp_config() -> dict:
    """Sample MCP configuration"""
    return {
        "base_url": "https://test.atlassian.net/wiki",
        "bearer_token": "test-token",
        "timeout": 30,
        "retry_count": 3,
        "space_key": "TEST",
        "page_ids": ["123456"]
    }


@pytest.fixture
def sample_retrieval_profile() -> dict:
    """Sample MCP retrieval profile"""
    return {
        "profile_name": "test_profile",
        "source_types": ["page", "attachment"],
        "content_types": ["application/pdf", "text/plain"],
        "page_filters": {"space": "TEST"},
        "max_results": 50,
        "freshness_days": 90
    }

# Made with Bob
