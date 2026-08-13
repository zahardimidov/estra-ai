import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pytest

from domain.entities import ModerationTask
from domain.services.moderation import ModerationService

# --- Fakes ---

@dataclass
class FakeTask:
    user_id: str
    input_type: str
    status: str
    categories: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime = field(default_factory=datetime.now)
    text_content: Optional[str] = None
    image_s3_path: Optional[str] = None
    callback_url: Optional[str] = None
    decision: Optional[str] = None
    scores_json: Optional[dict] = None
    model_versions_used: Optional[dict] = None


class FakeTaskRepository:
    def __init__(self):
        self._storage: list[FakeTask] = []

    async def create(self, **data) -> FakeTask:
        task = FakeTask(**data)
        self._storage.append(task)
        return task

    async def get(self, task_id: str) -> Optional[FakeTask]:
        return next((t for t in self._storage if t.id == task_id), None)


class FakeUoW:
    def __init__(self):
        self.tasks = FakeTaskRepository()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class FakeTaskQueue:
    def __init__(self):
        self._items: list[str] = []

    async def push(self, task_id: str) -> None:
        self._items.append(task_id)

    async def pop(self, timeout: int = 0) -> Optional[str]:
        return self._items.pop(0) if self._items else None

    async def size(self) -> int:
        return len(self._items)


class FakeS3Client:
    def __init__(self):
        self.uploaded_bytes: list[tuple[bytes, str]] = []
        self.uploaded_urls: list[str] = []

    async def upload_bytes(self, data: bytes, content_type: str = "image/jpeg") -> str:
        self.uploaded_bytes.append((data, content_type))
        return f"images/fake-{uuid.uuid4()}.jpeg"

    async def upload_from_url(self, url: str) -> str:
        self.uploaded_urls.append(url)
        return f"images/fake-{uuid.uuid4()}.jpeg"


def make_service(uow=None, queue=None, s3=None):
    return ModerationService(
        uow=uow or FakeUoW(),
        queue=queue or FakeTaskQueue(),
        s3=s3 or FakeS3Client(),
    )


# --- submit_text_task ---

async def test_submit_text_task_returns_task_id():
    service = make_service()

    task_id = await service.submit_text_task(user_id="u1", text_content="hello")

    assert isinstance(task_id, str) and len(task_id) > 0


async def test_submit_text_task_pushes_to_queue():
    queue = FakeTaskQueue()
    service = make_service(queue=queue)

    task_id = await service.submit_text_task(user_id="u1", text_content="hello")

    assert await queue.size() == 1
    assert (await queue.pop()) == task_id


async def test_submit_text_task_stores_correct_fields():
    uow = FakeUoW()
    service = make_service(uow=uow)

    task_id = await service.submit_text_task(
        user_id="u1", text_content="buy crypto now", callback_url="https://cb.example.com"
    )

    task = await uow.tasks.get(task_id)
    assert task.status == "pending"
    assert task.input_type == "text"
    assert task.text_content == "buy crypto now"
    assert task.callback_url == "https://cb.example.com"


# --- submit_image_task ---

async def test_submit_image_task_with_bytes_uploads_to_s3():
    s3 = FakeS3Client()
    service = make_service(s3=s3)
    image_data = b"fake-image-bytes"

    await service.submit_image_task(user_id="u1", image_bytes=image_data)

    assert len(s3.uploaded_bytes) == 1
    assert s3.uploaded_bytes[0][0] == image_data


async def test_submit_image_task_with_url_uploads_to_s3():
    s3 = FakeS3Client()
    service = make_service(s3=s3)
    url = "https://example.com/photo.jpg"

    await service.submit_image_task(user_id="u1", image_url=url)

    assert len(s3.uploaded_urls) == 1
    assert s3.uploaded_urls[0] == url


async def test_submit_image_task_stores_s3_path():
    uow = FakeUoW()
    s3 = FakeS3Client()
    service = make_service(uow=uow, s3=s3)

    task_id = await service.submit_image_task(user_id="u1", image_bytes=b"data")

    task = await uow.tasks.get(task_id)
    assert task.input_type == "image"
    assert task.image_s3_path is not None
    assert task.image_s3_path.startswith("images/")


async def test_submit_image_task_no_source_raises():
    service = make_service()

    with pytest.raises(ValueError, match="Either image_bytes or image_url must be provided"):
        await service.submit_image_task(user_id="u1")


async def test_submit_image_task_pushes_to_queue():
    queue = FakeTaskQueue()
    service = make_service(queue=queue)

    task_id = await service.submit_image_task(user_id="u1", image_bytes=b"data")

    assert (await queue.pop()) == task_id


# --- get_task ---

async def test_get_task_returns_entity():
    uow = FakeUoW()
    service = make_service(uow=uow)
    task_id = await service.submit_text_task(user_id="u1", text_content="check this")

    result = await service.get_task(task_id)

    assert isinstance(result, ModerationTask)
    assert result.id == task_id
    assert result.status == "pending"
    assert result.decision is None
    assert result.scores is None


async def test_get_task_not_found_returns_none():
    service = make_service()

    result = await service.get_task("nonexistent-id")

    assert result is None
