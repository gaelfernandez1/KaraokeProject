from __future__ import annotations

import redis

from karaoke.config import Settings

# How long a queued task stays attributed to its owner. Tasks finish well within
# a day; after that the key is irrelevant.
_TTL_SECONDS = 24 * 60 * 60

_cached_client: redis.Redis | None = None


def _redis() -> redis.Redis:
    global _cached_client
    if _cached_client is None:
        _cached_client = redis.from_url(Settings().redis_url, decode_responses=True)
    return _cached_client


def _key(task_id: str) -> str:
    return f"task:{task_id}:user_id"


def record_task_owner(task_id: str, user_id: str) -> None:
    _redis().setex(_key(task_id), _TTL_SECONDS, user_id)


def get_task_owner(task_id: str) -> str | None:
    return _redis().get(_key(task_id))
