"""Redis-backed history and rate limiting."""
import json
import time
from typing import Optional


class HistoryStore:
    """User history and rate limiting with Redis (graceful fallback to in-memory)."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0", max_history: int = 50):
        self.max_history = max_history
        self.redis = None
        self._memory_history: dict[int, list] = {}
        self._memory_rates: dict[int, list] = {}
        try:
            import redis as redis_lib
            self.redis = redis_lib.from_url(redis_url, decode_responses=True)
            self.redis.ping()
        except Exception:
            self.redis = None

    def add_record(self, user_id: int, platform: str, product: str, result_preview: str):
        """Save a generation record."""
        record = {
            "platform": platform,
            "product": product,
            "preview": result_preview[:200],
            "ts": int(time.time()),
        }
        if self.redis:
            key = f"history:{user_id}"
            self.redis.lpush(key, json.dumps(record))
            self.redis.ltrim(key, 0, self.max_history - 1)
        else:
            if user_id not in self._memory_history:
                self._memory_history[user_id] = []
            self._memory_history[user_id].insert(0, record)
            self._memory_history[user_id] = self._memory_history[user_id][:self.max_history]

    def get_history(self, user_id: int, limit: int = 10) -> list[dict]:
        """Get recent generation history."""
        if self.redis:
            key = f"history:{user_id}"
            items = self.redis.lrange(key, 0, limit - 1)
            return [json.loads(i) for i in items]
        return self._memory_history.get(user_id, [])[:limit]

    def check_rate_limit(self, user_id: int, max_per_min: int = 10) -> bool:
        """Return True if user is within rate limit."""
        now = time.time()
        if self.redis:
            key = f"rate:{user_id}"
            pipe = self.redis.pipeline()
            pipe.zadd(key, {str(now): now})
            pipe.zremrangebyscore(key, 0, now - 60)
            pipe.zcard(key)
            pipe.expire(key, 120)
            results = pipe.execute()
            return results[2] <= max_per_min
        else:
            if user_id not in self._memory_rates:
                self._memory_rates[user_id] = []
            self._memory_rates[user_id] = [t for t in self._memory_rates[user_id] if t > now - 60]
            self._memory_rates[user_id].append(now)
            return len(self._memory_rates[user_id]) <= max_per_min

    def get_stats(self, user_id: int) -> dict:
        """Get user usage stats."""
        history = self.get_history(user_id, limit=self.max_history)
        platforms = {}
        for r in history:
            p = r.get("platform", "unknown")
            platforms[p] = platforms.get(p, 0) + 1
        return {
            "total": len(history),
            "platforms": platforms,
        }
