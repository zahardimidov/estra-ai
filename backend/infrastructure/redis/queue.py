import redis.asyncio as aioredis

QUEUE_KEY = "estra:moderation_queue"


class TaskQueue:
    def __init__(self, client: aioredis.Redis):
        self.client = client

    async def push(self, task_id: str) -> None:
        await self.client.lpush(QUEUE_KEY, task_id)

    async def pop(self, timeout: int = 0) -> str | None:
        result = await self.client.brpop(QUEUE_KEY, timeout=timeout)
        if result:
            return result[1]
        return None

    async def size(self) -> int:
        return await self.client.llen(QUEUE_KEY)
