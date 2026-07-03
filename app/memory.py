import json
import os
from functools import lru_cache

from upstash_redis import Redis

MAX_HISTORY_TURNS = int(os.getenv("MEMORY_MAX_TURNS", "20"))
SESSION_TTL_SECONDS = int(os.getenv("MEMORY_TTL_SECONDS", "86400"))


@lru_cache(maxsize=1)
def _get_client() -> Redis:
    return Redis.from_env()


def _session_key(session_id: str) -> str:
    return f"session:{session_id}:history"


def get_history(session_id: str) -> list[dict]:
    raw_items = _get_client().lrange(_session_key(session_id), 0, -1)
    return [json.loads(item) for item in raw_items]


def append_turn(session_id: str, role: str, content: str) -> None:
    key = _session_key(session_id)
    client = _get_client()
    client.rpush(key, json.dumps({"role": role, "content": content}))
    client.ltrim(key, -MAX_HISTORY_TURNS, -1)
    client.expire(key, SESSION_TTL_SECONDS)


def clear_session(session_id: str) -> None:
    _get_client().delete(_session_key(session_id))
