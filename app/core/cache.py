"""Redis cache helpers for task list responses."""

from __future__ import annotations

import json
from typing import Any, Optional

import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

TASK_LIST_TTL_SECONDS = 60

_client: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def task_list_cache_key(
    project_id: int,
    *,
    status: Optional[str],
    priority: Optional[str],
    assignee_id: Optional[int],
    sort_by: str,
    skip: int,
    limit: int,
) -> str:
    return (
        f"tasks:list:{project_id}:"
        f"{status}:{priority}:{assignee_id}:{sort_by}:{skip}:{limit}"
    )


async def cache_get_json(key: str) -> Optional[Any]:
    if not settings.CACHE_ENABLED:
        return None
    try:
        client = await get_redis()
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        logger.warning("cache_get_failed", key=key)
        return None


async def cache_set_json(
    key: str,
    value: Any,
    *,
    ttl: int = TASK_LIST_TTL_SECONDS,
) -> None:
    if not settings.CACHE_ENABLED:
        return
    try:
        client = await get_redis()
        await client.set(key, json.dumps(value), ex=ttl)
    except Exception:
        logger.warning("cache_set_failed", key=key)


async def invalidate_project_task_list(project_id: int) -> None:
    if not settings.CACHE_ENABLED:
        return
    pattern = f"tasks:list:{project_id}:*"
    try:
        client = await get_redis()
        keys: list[str] = []
        async for key in client.scan_iter(match=pattern, count=100):
            keys.append(key)
        if keys:
            await client.delete(*keys)
    except Exception:
        logger.warning("cache_invalidate_failed", project_id=project_id)
