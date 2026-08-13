from datetime import date

import redis.asyncio as aioredis

SECONDS_IN_DAY = 86400


class RateLimiter:
    """Fixed daily-window counter backed by Redis. Key-agnostic — the caller
    decides what `identifier` means (api key id, user id, ...)."""

    def __init__(self, client: aioredis.Redis):
        self.client = client

    async def check_and_increment(self, identifier: str, limit: int) -> bool:
        key = f"ratelimit:{identifier}:{date.today().isoformat()}"
        count = await self.client.incr(key)
        if count == 1:
            await self.client.expire(key, SECONDS_IN_DAY)
        return count <= limit
