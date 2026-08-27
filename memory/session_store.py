"""Redis-backed session store for agent memory and task queuing."""
import json
from typing import Any, Optional

import redis.asyncio as aioredis
from loguru import logger

from models.schemas import get_settings

settings = get_settings()

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def close_redis():
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


# ── Session key-value store ───────────────────────────────────────────────────

SESSION_TTL = 60 * 60 * 24  # 24 hours


def _key(session_id: str, key: str) -> str:
    return f"session:{session_id}:kv:{key}"


async def memory_set(session_id: str, key: str, value: Any) -> bool:
    r = await get_redis()
    serialized = json.dumps(value)
    await r.set(_key(session_id, key), serialized, ex=SESSION_TTL)
    return True


async def memory_get(session_id: str, key: str) -> Optional[Any]:
    r = await get_redis()
    raw = await r.get(_key(session_id, key))
    if raw is None:
        return None
    return json.loads(raw)


# ── SSE pub/sub for streaming agent events ────────────────────────────────────

def _event_channel(task_id: str) -> str:
    return f"task:{task_id}:events"


async def publish_event(task_id: str, event: dict):
    r = await get_redis()
    await r.publish(_event_channel(task_id), json.dumps(event))


async def subscribe_events(task_id: str):
    """Async generator yielding events published for a task."""
    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe(_event_channel(task_id))
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                yield json.loads(message["data"])
    finally:
        await pubsub.unsubscribe(_event_channel(task_id))
        await pubsub.aclose()
