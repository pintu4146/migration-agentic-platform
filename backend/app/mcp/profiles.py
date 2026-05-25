"""
MCP Retrieval Profiles

Defines retrieval profiles for different agent contexts.
"""

from typing import Dict, Any, List, Optional
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, field_validator


class ProfileType(str, Enum):
    """Predefined profile types"""
    CONTEXT_RETRIEVAL = "context_retrieval"
    EXTRACTION = "extraction"
    QUESTIONNAIRE = "questionnaire"
    PLANNING = "planning"
    REVIEW = "review"
    CUSTOM = "custom"


class RetrievalProfile(BaseModel):
    """
    Retrieval profile configuration.
    
    Defines what and how to retrieve from MCP Gateway.
    """
    
    profile_name: str = Field(description="Profile identifier")
    profile_type: ProfileType = Field(
        default=ProfileType.CUSTOM,
        description="Profile type"
    )
    
    # Source filters
    source_types: Optional[List[str]] = Field(
        default=None,
        description="Source types to retrieve (page, attachment, etc.)"
    )
    content_types: Optional[List[str]] = Field(
        default=None,
        description="Content MIME types to filter"
    )
    
    # Page filters
    page_filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Page-specific filters (space, labels, etc.)"
    )
    
    # Attachment filters
    attachment_filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Attachment-specific filters"
    )
    
    # Content filters
    keyword_filters: Optional[List[str]] = Field(
        default=None,
        description="Keywords to filter content"
    )
    section_filters: Optional[List[str]] = Field(
        default=None,
        description="Section names to extract"
    )
    
    # Retrieval limits
    max_results: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of results"
    )
    
    # Freshness
    freshness_days: Optional[int] = Field(
        default=None,
        ge=1,
        description="Only retrieve content modified within N days"
    )
    
    # Additional options
    include_metadata: bool = Field(
        default=True,
        description="Include document metadata"
    )
    include_attachments: bool = Field(
        default=True,
        description="Include attachments"
    )
    include_comments: bool = Field(
        default=False,
        description="Include comments"
    )
    
    # MCP-specific options
    mcp_options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional MCP-specific options"
    )
    
    @field_validator('profile_name')
    @classmethod
    def validate_profile_name(cls, v: str) -> str:
        """Validate profile name"""
        if not v or not v.strip():
            raise ValueError("Profile name cannot be empty")
        return v.strip()
    
    @field_validator('keyword_filters')
    @classmethod
    def validate_keywords(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate and normalize keywords"""
        if v is None:
            return None
        return [k.strip().lower() for k in v if k.strip()]
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "profile_name": "extraction_profile",
            "profile_type": "extraction",
            "source_types": ["page", "attachment"],
            "content_types": ["application/pdf", "text/plain"],
            "page_filters": {"space": "PROJ"},
            "max_results": 50,
            "freshness_days": 90
        }
    })


# Predefined profiles
PREDEFINED_PROFILES: Dict[ProfileType, RetrievalProfile] = {
    ProfileType.CONTEXT_RETRIEVAL: RetrievalProfile(
        profile_name="context_retrieval_profile",
        profile_type=ProfileType.CONTEXT_RETRIEVAL,
        source_types=["page", "attachment", "blog"],
        max_results=200,
        include_metadata=True,
        include_attachments=True,
        include_comments=False,
        mcp_options={
            "expand": ["body.storage", "metadata.labels", "version"],
            "depth": 2
        }
    ),
    
    ProfileType.EXTRACTION: RetrievalProfile(
        profile_name="extraction_profile",
        profile_type=ProfileType.EXTRACTION,
        source_types=["page", "attachment"],
        content_types=[
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain"
        ],
        keyword_filters=[
            "architecture",
            "technical",
            "infrastructure",
            "deployment",
            "configuration"
        ],
        max_results=100,
        freshness_days=180,
        include_metadata=True,
        include_attachments=True,
        mcp_options={
            "expand": ["body.storage", "metadata.labels"],
            "depth": 1
        }
    ),
    
    ProfileType.QUESTIONNAIRE: RetrievalProfile(
        profile_name="questionnaire_profile",
        profile_type=ProfileType.QUESTIONNAIRE,
        source_types=["page"],
        keyword_filters=[
            "requirements",
            "specification",
            "constraints",
            "dependencies"
        ],
        section_filters=[
            "requirements",
            "dependencies",
            "constraints",
            "assumptions"
        ],
        max_results=50,
        freshness_days=90,
        include_metadata=True,
        include_attachments=False,
        include_comments=True,
        mcp_options={
            "expand": ["body.storage", "metadata.labels", "children.comment"],
            "depth": 1
        }
    ),
    
    ProfileType.PLANNING: RetrievalProfile(
        profile_name="planning_profile",
        profile_type=ProfileType.PLANNING,
        source_types=["page", "blog"],
        keyword_filters=[
            "migration",
            "strategy",
            "roadmap",
            "timeline",
            "phases"
        ],
        section_filters=[
            "migration strategy",
            "implementation plan",
            "timeline",
            "phases"
        ],
        max_results=75,
        freshness_days=365,
        include_metadata=True,
        include_attachments=True,
        mcp_options={
            "expand": ["body.storage", "metadata.labels", "version"],
            "depth": 1
        }
    ),
    
    ProfileType.REVIEW: RetrievalProfile(
        profile_name="review_profile",
        profile_type=ProfileType.REVIEW,
        source_types=["page", "comment"],
        keyword_filters=[
            "review",
            "validation",
            "verification",
            "approval"
        ],
        max_results=50,
        freshness_days=30,
        include_metadata=True,
        include_attachments=False,
        include_comments=True,
        mcp_options={
            "expand": ["body.storage", "metadata.labels", "children.comment", "version"],
            "depth": 1
        }
    )
}


def get_profile(profile_type: ProfileType) -> RetrievalProfile:
    """
    Get a predefined retrieval profile.
    
    Args:
        profile_type: Profile type to retrieve
        
    Returns:
        RetrievalProfile instance
        
    Raises:
        ValueError: If profile type not found
    """
    if profile_type not in PREDEFINED_PROFILES:
        raise ValueError(f"Unknown profile type: {profile_type}")
    
    return PREDEFINED_PROFILES[profile_type].model_copy(deep=True)


def create_custom_profile(
    name: str,
    base_profile: Optional[ProfileType] = None,
    **overrides
) -> RetrievalProfile:
    """
    Create a custom profile, optionally based on a predefined one.
    
    Args:
        name: Custom profile name
        base_profile: Optional base profile to extend
        **overrides: Profile field overrides
        
    Returns:
        Custom RetrievalProfile instance
    """
    if base_profile:
        # Start with base profile
        profile_dict = get_profile(base_profile).model_dump()
        profile_dict.update(overrides)
        profile_dict["profile_name"] = name
        profile_dict["profile_type"] = ProfileType.CUSTOM
        return RetrievalProfile(**profile_dict)
    else:
        # Create from scratch
        return RetrievalProfile(
            profile_name=name,
            profile_type=ProfileType.CUSTOM,
            **overrides
        )

# Made with Bob
