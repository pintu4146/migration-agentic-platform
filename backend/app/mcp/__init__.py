"""
MCP (Model Context Protocol) Connector Module

Provides plug-and-play knowledge retrieval from IBM Context Studio Gateway.
"""

from .connector import MCPConnector
from .profiles import RetrievalProfile, ProfileType
from .models import ContextPack, Document, DocumentMetadata

__all__ = [
    "MCPConnector",
    "RetrievalProfile",
    "ProfileType",
    "ContextPack",
    "Document",
    "DocumentMetadata",
]

# Made with Bob
