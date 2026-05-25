"""
Qdrant Search Profiles

Defines search profiles for Qdrant vector store.
Mirrors MCP profiles for consistent retrieval interface.

Design: DRY - Reusable profile configurations
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class QdrantSearchProfile(BaseModel):
    """
    Qdrant search configuration.
    
    Matches MCP RetrievalProfile structure for consistency.
    """
    
    profile_name: str = Field(description="Profile identifier")
    profile_type: str = Field(description="Profile type (extraction, questionnaire, etc.)")
    
    # Collection settings
    collection_name: str = Field(
        default="migration_context",
        description="Qdrant collection name"
    )
    
    # Search parameters
    limit: int = Field(default=50, description="Max results to return")
    score_threshold: float = Field(
        default=0.7,
        description="Minimum similarity score (0.0-1.0)"
    )
    
    # Filters
    metadata_filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadata filters (e.g., doc_type, source)"
    )
    content_type_filter: Optional[List[str]] = Field(
        default=None,
        description="Filter by content types"
    )
    
    # Vector search options
    with_payload: bool = Field(default=True, description="Include document payload")
    with_vectors: bool = Field(default=False, description="Include vectors in response")


# Predefined profiles matching MCP profiles
QDRANT_PROFILES: Dict[str, QdrantSearchProfile] = {
    "extraction_profile": QdrantSearchProfile(
        profile_name="extraction_profile",
        profile_type="extraction",
        limit=100,
        score_threshold=0.6,
        metadata_filters={"doc_type": ["technical", "architecture", "code"]}
    ),
    
    "questionnaire_profile": QdrantSearchProfile(
        profile_name="questionnaire_profile",
        profile_type="questionnaire",
        limit=50,
        score_threshold=0.7,
        metadata_filters={"doc_type": ["requirements", "specifications", "documentation"]}
    ),
    
    "planning_profile": QdrantSearchProfile(
        profile_name="planning_profile",
        profile_type="planning",
        limit=75,
        score_threshold=0.65,
        metadata_filters={"doc_type": ["architecture", "infrastructure", "deployment"]}
    ),
    
    "review_profile": QdrantSearchProfile(
        profile_name="review_profile",
        profile_type="review",
        limit=30,
        score_threshold=0.75,
        metadata_filters={"doc_type": ["review", "validation", "testing"]}
    ),
    
    "context_retrieval_profile": QdrantSearchProfile(
        profile_name="context_retrieval_profile",
        profile_type="context_retrieval",
        limit=200,
        score_threshold=0.5,
        metadata_filters=None  # Broad search
    ),
}


def get_qdrant_profile(profile_name: str) -> QdrantSearchProfile:
    """
    Get Qdrant profile by name.
    
    Args:
        profile_name: Profile identifier
        
    Returns:
        QdrantSearchProfile
        
    Raises:
        ValueError: If profile not found
    """
    profile = QDRANT_PROFILES.get(profile_name)
    if not profile:
        raise ValueError(
            f"Qdrant profile '{profile_name}' not found. "
            f"Available: {list(QDRANT_PROFILES.keys())}"
        )
    return profile

# Made with Bob
