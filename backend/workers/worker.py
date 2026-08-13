"""
ML Worker entry point.

Run with:
    python -m workers.worker

The worker runs in an infinite loop, blocking on the Redis queue.
On each iteration it pops a task_id, processes it, and loops again.
"""
import asyncio
import logging

from prometheus_client import start_http_server

from core.logging import setup_logging
from infrastructure.db.session import async_session
from infrastructure.db.uow import SqlAlchemyUnitOfWork
from infrastructure.monitoring.metrics_worker import queue_size
from infrastructure.redis.client import redis_client
from infrastructure.redis.queue import TaskQueue
from workers.tasks import process_task

logger = logging.getLogger(__name__)

BRPOP_TIMEOUT = 5  # seconds; 0 = block indefinitely
METRICS_PORT = 8001


async def _run() -> None:
    setup_logging()
    start_http_server(METRICS_PORT)
    logger.info("Worker started — waiting for tasks on queue")

    queue = TaskQueue(redis_client)

    while True:
        try:
            queue_size.set(await queue.size())
            task_id = await queue.pop(timeout=BRPOP_TIMEOUT)
        except Exception:
            logger.exception("Failed to pop from Redis queue, retrying in 2s")
            await asyncio.sleep(2)
            continue

        if task_id is None:
            # Timeout expired, no tasks — loop again
            continue

        try:
            uow = SqlAlchemyUnitOfWork(async_session)
            await process_task(task_id, uow)
        except Exception:
            logger.exception("Unhandled error while processing task %s", task_id)


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
