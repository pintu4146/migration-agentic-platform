"""
Tests for MCP Connector Module
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.mcp.connector import MCPConnector
from app.mcp.profiles import RetrievalProfile, ProfileType, get_profile
from app.mcp.models import (
    Document,
    DocumentType,
    DocumentSource,
    DocumentMetadata,
    ContextPack,
    MCPError
)


class TestRetrievalProfiles:
    """Test retrieval profile functionality"""
    
    def test_get_predefined_profile(self):
        """Test getting a predefined profile"""
        profile = get_profile(ProfileType.EXTRACTION)
        
        assert profile.profile_name == "extraction_profile"
        assert profile.profile_type == ProfileType.EXTRACTION
        assert profile.max_results == 100
        assert "page" in profile.source_types
    
    def test_profile_validation(self):
        """Test profile validation"""
        # Valid profile
        profile = RetrievalProfile(
            profile_name="test_profile",
            max_results=50
        )
        assert profile.profile_name == "test_profile"
        
        # Invalid profile name
        with pytest.raises(ValueError):
            RetrievalProfile(profile_name="", max_results=50)
    
    def test_keyword_normalization(self):
        """Test keyword filter normalization"""
        profile = RetrievalProfile(
            profile_name="test",
            keyword_filters=["  Architecture  ", "MIGRATION", "test"]
        )
        
        assert profile.keyword_filters == ["architecture", "migration", "test"]


class TestMCPConnector:
    """Test MCP connector functionality"""
    
    def test_connector_initialization(self):
        """Test connector initialization"""
        with pytest.raises(ValueError, match="MCP Gateway URL not configured"):
            MCPConnector(gateway_url=None)
    
    def test_connector_with_config(self):
        """Test connector with valid configuration"""
        connector = MCPConnector(
            gateway_url="https://test.example.com/mcp",
            gateway_token="test-token",
            api_key="test-key"
        )
        
        assert connector.gateway_url == "https://test.example.com/mcp"
        assert connector.gateway_token == "test-token"
        assert connector.api_key == "test-key"
    
    def test_headers_generation(self):
        """Test HTTP headers generation"""
        connector = MCPConnector(
            gateway_url="https://test.example.com/mcp",
            gateway_token="test-token",
            api_key="test-key"
        )
        
        headers = connector._get_headers()
        
        assert headers["Authorization"] == "Bearer test-token"
        assert headers["x-api-key"] == "test-key"
        assert headers["Content-Type"] == "application/json"
    
    def test_cache_key_generation(self):
        """Test cache key generation"""
        connector = MCPConnector(
            gateway_url="https://test.example.com/mcp",
            gateway_token="test-token",
            api_key="test-key"
        )
        
        profile = RetrievalProfile(profile_name="test", max_results=50)
        cache_key = connector._generate_cache_key("proj_123", profile)
        
        assert isinstance(cache_key, str)
        assert len(cache_key) == 16


class TestDocumentModels:
    """Test document data models"""
    
    def test_document_creation(self):
        """Test document model creation"""
        metadata = DocumentMetadata(
            source_id="page_123",
            author="test@example.com",
            space="TEST"
        )
        
        doc = Document(
            id="doc_123",
            source=DocumentSource.CONTEXT_STUDIO,
            type=DocumentType.PAGE,
            title="Test Document",
            content="Test content",
            metadata=metadata,
            confidence=0.95
        )
        
        assert doc.id == "doc_123"
        assert doc.source == DocumentSource.CONTEXT_STUDIO
        assert doc.type == DocumentType.PAGE
        assert doc.confidence == 0.95
    
    def test_context_pack_creation(self):
        """Test context pack creation"""
        doc = Document(
            id="doc_123",
            source=DocumentSource.CONTEXT_STUDIO,
            type=DocumentType.PAGE,
            title="Test",
            content="Content",
            metadata=DocumentMetadata(source_id="123")
        )
        
        context_pack = ContextPack(
            project_id="proj_123",
            profile_name="test_profile",
            documents=[doc],
            total_count=1
        )
        
        assert context_pack.project_id == "proj_123"
        assert len(context_pack.documents) == 1
        assert context_pack.total_count == 1


@pytest.mark.asyncio
class TestMCPConnectorAsync:
    """Test async MCP connector operations"""
    
    async def test_health_check_success(self):
        """Test successful health check"""
        connector = MCPConnector(
            gateway_url="https://test.example.com/mcp",
            gateway_token="test-token",
            api_key="test-key"
        )
        
        with patch.object(connector, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_request.return_value = mock_response
            
            result = await connector.health_check()
            assert result is True
    
    async def test_health_check_failure(self):
        """Test failed health check"""
        connector = MCPConnector(
            gateway_url="https://test.example.com/mcp",
            gateway_token="test-token",
            api_key="test-key"
        )
        
        with patch.object(connector, '_make_request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = Exception("Connection failed")
            
            result = await connector.health_check()
            assert result is False

# Made with Bob
