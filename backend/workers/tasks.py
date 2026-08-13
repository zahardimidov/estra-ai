"""
Task processor: fetches a task from DB, runs ML inference, persists results,
and sends a webhook callback if configured.
"""
import logging
import time

import aiohttp

from infrastructure.db.uow import SqlAlchemyUnitOfWork
from infrastructure.monitoring.metrics_worker import (
    blocked_tasks_total,
    ml_inference_time,
    processed_tasks_total,
)
from ml.inference import run_image_inference, run_text_inference

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 10


async def process_task(task_id: str, uow: SqlAlchemyUnitOfWork) -> None:
    async with uow as u:
        task = await u.tasks.get(task_id)
        if task is None:
            logger.warning("Task %s not found in DB, skipping", task_id)
            return
        await u.tasks.update_status(task_id, status="processing")

    logger.info("Processing task %s (type=%s, categories=%s)", task_id, task.input_type, task.categories)

    try:
        inference_start = time.perf_counter()
        if task.input_type == "text":
            scores, model_versions, decision = run_text_inference(
                text=task.text_content or "",
                categories=task.categories or [],
            )
        else:
            scores, model_versions, decision = run_image_inference(
                categories=task.categories or [],
            )
        ml_inference_time.labels(task.input_type).observe(time.perf_counter() - inference_start)

    except Exception:
        logger.exception("Unexpected error during inference for task %s", task_id)
        async with uow as u:
            await u.tasks.update_status(task_id, status="failed")
        return

    async with uow as u:
        await u.tasks.update_status(
            task_id,
            status="completed",
            decision=decision,
            scores_json=scores,
            model_versions_used=model_versions,
        )

    processed_tasks_total.inc()
    if decision == "blocked":
        blocked_tasks_total.inc()

    logger.info("Task %s completed — decision=%s scores=%s", task_id, decision, scores)

    if task.callback_url:
        await _send_webhook(
            url=task.callback_url,
            payload={
                "task_id": task_id,
                "status": "completed",
                "decision": decision,
                "scores": scores,
                "model_versions": model_versions,
            },
        )


async def _send_webhook(url: str, payload: dict) -> None:
    try:
        timeout = aiohttp.ClientTimeout(total=WEBHOOK_TIMEOUT_SECONDS)
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.post(url, json=payload) as response,
        ):
            logger.info("Webhook → %s  status=%s", url, response.status)
    except Exception:
        logger.warning("Webhook delivery failed for %s", url, exc_info=True)
