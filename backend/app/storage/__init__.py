"""
Storage Layer

Provides data persistence and caching services.
Follows Single Responsibility Principle - each client handles one storage type.
"""

from .redis_client import RedisClient
from .qdrant_client import QdrantClient

__all__ = [
    "RedisClient",
    "QdrantClient",
]

# Made with Bob
