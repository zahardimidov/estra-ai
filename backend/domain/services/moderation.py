from typing import Optional

from domain.entities import ModerationTask
from infrastructure.db.uow import SqlAlchemyUnitOfWork
from infrastructure.redis.queue import TaskQueue
from infrastructure.storage.s3_client import S3Client

DEFAULT_TEXT_CATEGORIES = ("spam", "toxicity", "scam")
DEFAULT_IMAGE_CATEGORIES = ("nsfw",)


class ModerationService:
    def __init__(self, uow: SqlAlchemyUnitOfWork, queue: TaskQueue, s3: S3Client):
        self.uow = uow
        self.queue = queue
        self.s3 = s3

    async def _create_and_enqueue(self, **task_data) -> str:
        async with self.uow as uow:
            task = await uow.tasks.create(**task_data)
            task_id = task.id
        await self.queue.push(task_id)
        return task_id

    async def submit_text_task(
        self,
        user_id: str,
        text_content: str,
        categories: list[str] = DEFAULT_TEXT_CATEGORIES,
        callback_url: Optional[str] = None,
    ) -> str:
        return await self._create_and_enqueue(
            user_id=user_id,
            input_type="text",
            text_content=text_content,
            categories=categories,
            callback_url=callback_url,
            status="pending",
        )

    async def submit_image_task(
        self,
        user_id: str,
        image_bytes: Optional[bytes] = None,
        image_url: Optional[str] = None,
        content_type: str = "image/jpeg",
        categories: list[str] = DEFAULT_IMAGE_CATEGORIES,
        callback_url: Optional[str] = None,
    ) -> str:
        if image_bytes is None and not image_url:
            raise ValueError("Either image_bytes or image_url must be provided")

        if image_url:
            s3_path = await self.s3.upload_from_url(image_url)
        else:
            assert image_bytes is not None
            s3_path = await self.s3.upload_bytes(image_bytes, content_type)

        return await self._create_and_enqueue(
            user_id=user_id,
            input_type="image",
            image_s3_path=s3_path,
            categories=categories,
            callback_url=callback_url,
            status="pending",
        )

    async def get_task(self, task_id: str) -> Optional[ModerationTask]:
        async with self.uow as uow:
            task = await uow.tasks.get(task_id)

        if task is None:
            return None

        return ModerationTask(
            id=task.id,
            user_id=task.user_id,
            status=task.status,
            categories=task.categories or [],
            decision=task.decision,
            scores=task.scores_json,
            model_versions=task.model_versions_used,
            created_at=task.created_at,
            completed_at=task.completed_at
        )
