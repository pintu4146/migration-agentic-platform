"""
Redis Client

Handles state caching and session management.
Follows Single Responsibility Principle - only Redis operations.
"""

import json
import logging
from typing import Optional, Any, Dict
from datetime import timedelta

import redis.asyncio as redis

from ..config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Async Redis client for state caching.
    
    Responsibilities:
    - Cache workflow state
    - Manage session data
    - Handle TTL expiration
    
    Design Principles:
    - KISS: Simple get/set/delete operations
    - DRY: Reusable serialization logic
    - SOLID: Single responsibility (Redis only)
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: Optional[int] = None,
        password: Optional[str] = None
    ):
        """Initialize Redis client with config."""
        self.host = host or settings.redis_host
        self.port = port or settings.redis_port
        self.db = db or settings.redis_db
        self.password = password or settings.redis_password
        self._client: Optional[redis.Redis] = None
    
    async def connect(self) -> None:
        """Establish Redis connection."""
        if self._client is None:
            self._client = await redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True
            )
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
            logger.info("Disconnected from Redis")
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get value from Redis.
        
        Args:
            key: Cache key
            
        Returns:
            Deserialized value or None
        """
        if not self._client:
            await self.connect()
        
        try:
            value = await self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in Redis with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time-to-live in seconds (default from settings)
            
        Returns:
            True if successful
        """
        if not self._client:
            await self.connect()
        
        try:
            serialized = json.dumps(value)
            ttl_seconds = ttl or settings.redis_ttl
            
            await self._client.setex(
                key,
                timedelta(seconds=ttl_seconds),
                serialized
            )
            return True
        except Exception as e:
            logger.error(f"Redis SET error for key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from Redis.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted
        """
        if not self._client:
            await self.connect()
        
        try:
            result = await self._client.delete(key)
            return result > 0
        except Exception as e:
            logger.error(f"Redis DELETE error for key '{key}': {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        if not self._client:
            await self.connect()
        
        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis EXISTS error for key '{key}': {e}")
            return False
    
    async def ping(self) -> bool:
        """Check Redis connection health."""
        if not self._client:
            await self.connect()
        
        try:
            return await self._client.ping()
        except Exception as e:
            logger.error(f"Redis PING error: {e}")
            return False
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


# Singleton instance
_redis_client: Optional[RedisClient] = None


async def get_redis_client() -> RedisClient:
    """
    Get or create Redis client singleton.
    
    Returns:
        RedisClient instance
    """
    global _redis_client
    
    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()
    
    return _redis_client

# Made with Bob
