import redis.asyncio as aioredis

from core.config import settings

redis_client = aioredis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True,
)
