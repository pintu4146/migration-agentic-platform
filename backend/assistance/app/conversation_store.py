"""
Conversation Store

Per-project Redis-backed chat history for the Advanced Assistance service.
Key pattern: assistance:{project_id}:history
Each entry is a dict with role, content, timestamp, and optional metadata.
"""

import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Redis TTL: 7 days — history scoped to active review window
HISTORY_TTL_SECONDS = 60 * 60 * 24 * 7
# Maximum messages kept per project (rolling window)
MAX_HISTORY_MESSAGES = 100


def _key(project_id: str) -> str:
    """Build the Redis key for a project's chat history."""
    return f"assistance:{project_id}:history"


class ConversationStore:
    """
    Per-project conversation history backed by Redis.

    Responsibilities:
    - Append user/assistant messages to project history
    - Return last N messages for context window
    - Clear history on demand

    Design:
    - Uses a Redis LIST (rpush / lrange) for ordered history
    - Each element is a JSON-encoded ChatMessage dict
    - Rolling window enforced by ltrim after every append
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialize the store.

        Args:
            redis_url: Full Redis connection URL.
        """
        self._redis_url = redis_url
        self._client: Optional[redis.Redis] = None

    async def _get_client(self) -> redis.Redis:
        """Lazy-connect and return the Redis client."""
        if self._client is None:
            self._client = await redis.from_url(
                self._redis_url,
                decode_responses=True,
            )
            logger.info("ConversationStore: connected to Redis at %s", self._redis_url)
        return self._client

    async def append(
        self,
        project_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Append a message to the project's conversation history.

        Args:
            project_id: Project identifier.
            role: "user" or "assistant".
            content: Message text.
            metadata: Optional extra fields (e.g., thought/action trace).
        """
        client = await self._get_client()
        key = _key(project_id)

        message: Dict[str, Any] = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if metadata:
            message["metadata"] = metadata

        serialized = json.dumps(message)
        await client.rpush(key, serialized)  # type: ignore[misc]
        # Keep only last MAX_HISTORY_MESSAGES entries (rolling window)
        await client.ltrim(key, -MAX_HISTORY_MESSAGES, -1)  # type: ignore[misc]
        await client.expire(key, HISTORY_TTL_SECONDS)  # type: ignore[misc]
        logger.debug(
            "ConversationStore: appended %s message for project %s",
            role,
            project_id,
        )

    async def get_history(
        self,
        project_id: str,
        last_n: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Return the last N messages for a project.

        Args:
            project_id: Project identifier.
            last_n: Number of recent messages to return (default 20).

        Returns:
            List of message dicts ordered oldest → newest.
        """
        client = await self._get_client()
        key = _key(project_id)

        raw_messages = await client.lrange(key, -last_n, -1)  # type: ignore[misc]
        messages: List[Dict[str, Any]] = []
        for raw in raw_messages:
            try:
                messages.append(json.loads(raw))
            except json.JSONDecodeError as exc:
                logger.warning(
                    "ConversationStore: failed to decode message: %s — %s",
                    raw,
                    exc,
                )
        return messages

    async def clear(self, project_id: str) -> None:
        """
        Delete all history for a project.

        Args:
            project_id: Project identifier.
        """
        client = await self._get_client()
        await client.delete(_key(project_id))  # type: ignore[misc]
        logger.info(
            "ConversationStore: cleared history for project %s", project_id
        )

    async def count(self, project_id: str) -> int:
        """
        Return the number of messages stored for a project.

        Args:
            project_id: Project identifier.

        Returns:
            Message count.
        """
        client = await self._get_client()
        return await client.llen(_key(project_id))  # type: ignore[misc]

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("ConversationStore: Redis connection closed")


# Module-level singleton — shared across the FastAPI lifespan
_store: Optional[ConversationStore] = None


def get_conversation_store(redis_url: str = "redis://localhost:6379/0") -> ConversationStore:
    """
    Return the module-level ConversationStore singleton.

    Args:
        redis_url: Redis connection URL (only used on first call).

    Returns:
        ConversationStore instance.
    """
    global _store
    if _store is None:
        _store = ConversationStore(redis_url=redis_url)
    return _store

# Made with Bob
