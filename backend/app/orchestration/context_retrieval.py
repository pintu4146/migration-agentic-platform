"""
Context Retrieval with Fallback

Unified context retrieval using MCP (primary) and Qdrant (fallback).
Follows SOLID principles with clear separation of concerns.
"""

import logging
from typing import Optional, Dict

from ..mcp.connector import MCPConnector
from ..mcp.models import ContextPack, MCPError
from ..mcp.profiles import get_profile, ProfileType
from ..storage.qdrant_client import QdrantClient
from ..storage.qdrant_profiles import get_qdrant_profile

logger = logging.getLogger(__name__)


class ContextRetrievalError(Exception):
    """Raised when all context sources fail."""
    pass


class ContextRetriever:
    """
    Unified context retrieval with automatic fallback.
    
    Responsibilities:
    - Try MCP first (primary source)
    - Fallback to Qdrant if MCP fails
    - Return consistent ContextPack format
    
    Design Principles:
    - SOLID: Single responsibility (context retrieval only)
    - KISS: Simple try-fallback logic
    - DRY: Reusable retrieval logic
    """
    
    def __init__(
        self,
        mcp_connector: MCPConnector,
        qdrant_client: QdrantClient
    ):
        """
        Initialize context retriever.
        
        Args:
            mcp_connector: MCP connector instance
            qdrant_client: Qdrant client instance
        """
        self.mcp = mcp_connector
        self.qdrant = qdrant_client
    
    async def retrieve(
        self,
        project_id: str,
        profile_name: str,
        query: Optional[str] = None
    ) -> ContextPack:
        """
        Retrieve context with automatic fallback.
        
        Strategy:
        1. Try MCP (IBM Context Studio) first
        2. If MCP fails or returns empty, try Qdrant
        3. If both fail, raise ContextRetrievalError
        
        Args:
            project_id: Context ID for MCP or project ID for Qdrant
            profile_name: Profile name (same for both sources)
            query: Optional search query
            
        Returns:
            ContextPack with documents from either source
            
        Raises:
            ContextRetrievalError: If all sources fail
        """
        # Try MCP first (primary source)
        context_pack = await self._try_mcp(project_id, profile_name, query)
        
        if context_pack and context_pack.total_count > 0:
            logger.info(
                f"✅ Retrieved {context_pack.total_count} docs from MCP "
                f"(profile={profile_name})"
            )
            return context_pack
        
        # Fallback to Qdrant (secondary source)
        logger.warning(
            f"⚠️  MCP returned {context_pack.total_count if context_pack else 0} docs. "
            f"Trying Qdrant fallback..."
        )
        
        context_pack = await self._try_qdrant(project_id, profile_name, query)
        
        if context_pack and context_pack.total_count > 0:
            logger.info(
                f"✅ Retrieved {context_pack.total_count} docs from Qdrant "
                f"(profile={profile_name})"
            )
            return context_pack
        
        # Both sources failed
        raise ContextRetrievalError(
            f"All context sources failed for profile '{profile_name}'. "
            f"MCP and Qdrant both returned no results."
        )
    
    async def _try_mcp(
        self,
        project_id: str,
        profile_name: str,
        query: Optional[str]
    ) -> Optional[ContextPack]:
        """
        Try to retrieve from MCP.
        
        Args:
            project_id: Context ID
            profile_name: Profile name
            query: Optional query
            
        Returns:
            ContextPack or None if failed
        """
        try:
            # Normalize profile name (remove _profile suffix if present)
            normalized_name = profile_name.replace("_profile", "")
            
            # Get MCP profile
            profile = get_profile(ProfileType(normalized_name))
            
            # Retrieve from MCP
            context_pack = await self.mcp.retrieve(
                profile=profile,
                project_id=project_id,
                query=query or ""
            )
            
            # Mark source
            context_pack.metadata["source"] = "mcp"
            
            return context_pack
            
        except MCPError as e:
            logger.warning(f"MCP retrieval failed: {e}")
            return None
        except Exception as e:
            logger.error(f"MCP unexpected error: {e}", exc_info=True)
            return None
    
    async def _try_qdrant(
        self,
        project_id: str,
        profile_name: str,
        query: Optional[str]
    ) -> Optional[ContextPack]:
        """
        Try to retrieve from Qdrant.
        
        Args:
            project_id: Project ID
            profile_name: Profile name
            query: Optional query
            
        Returns:
            ContextPack or None if failed
        """
        try:
            # Get Qdrant profile
            profile = get_qdrant_profile(profile_name)
            
            # Retrieve from Qdrant
            context_pack = await self.qdrant.search(
                profile=profile,
                query=query or "migration context",  # Default query
                project_id=project_id
            )
            
            # Mark source
            context_pack.metadata["source"] = "qdrant_fallback"
            
            return context_pack
            
        except Exception as e:
            logger.error(f"Qdrant retrieval failed: {e}", exc_info=True)
            return None
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of both context sources.
        
        Returns:
            Dict with health status of each source
        """
        return {
            "mcp": await self.mcp.health_check(),
            "qdrant": await self.qdrant.client.get_collections() is not None
        }


# Singleton instance
_context_retriever: Optional[ContextRetriever] = None


async def get_context_retriever() -> ContextRetriever:
    """
    Get or create ContextRetriever singleton.
    
    Returns:
        ContextRetriever instance
    """
    global _context_retriever
    
    if _context_retriever is None:
        from ..mcp.connector import MCPConnector
        from ..storage.qdrant_client import get_qdrant_client
        
        mcp_connector = MCPConnector()
        qdrant_client = get_qdrant_client()
        
        _context_retriever = ContextRetriever(
            mcp_connector=mcp_connector,
            qdrant_client=qdrant_client
        )
    
    return _context_retriever

# Made with Bob
