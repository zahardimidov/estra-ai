from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from pydantic import AnyHttpUrl

from api.dependencies import CurrentUser, enforce_rate_limit, get_moderation_service
from api.v1.schemas.moderation import (
    ModerateResponse,
    ModerateTextRequest,
    ModerationCategory,
    TaskStatusResponse,
)
from domain.services import ModerationService

router = APIRouter(tags=["Moderation"])

_DEFAULT_IMAGE_CATEGORIES = [ModerationCategory.nsfw]


@router.post("/moderate/text", response_model=ModerateResponse, status_code=202)
async def moderate_text(
    data: ModerateTextRequest,
    user: CurrentUser,
    service: ModerationService = Depends(get_moderation_service),
    _: None = Depends(enforce_rate_limit),
):
    task_id = await service.submit_text_task(
        user_id=user.id,
        text_content=data.text,
        categories=[c.value for c in data.categories],
        callback_url=str(data.callback_url) if data.callback_url else None,
    )
    return ModerateResponse(task_id=task_id, status="pending")


@router.post("/moderate/image", response_model=ModerateResponse, status_code=202)
async def moderate_image(
    file: UploadFile,
    user: CurrentUser,
    categories: Annotated[
        list[ModerationCategory],
        Query(),
    ] = _DEFAULT_IMAGE_CATEGORIES,
    callback_url: Optional[AnyHttpUrl] = None,
    service: ModerationService = Depends(get_moderation_service),
    _: None = Depends(enforce_rate_limit),
):
    image_bytes = await file.read()
    content_type = file.content_type or "image/jpeg"

    task_id = await service.submit_image_task(
        user_id=user.id,
        image_bytes=image_bytes,
        content_type=content_type,
        categories=[c.value for c in categories],
        callback_url=str(callback_url) if callback_url else None,
    )

    return ModerateResponse(task_id=task_id, status="pending")


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse, status_code=200)
async def get_task(
    task_id: str,
    user: CurrentUser,
    service: ModerationService = Depends(get_moderation_service),
):
    task = await service.get_task(task_id)
    if task is None or task.user_id != user.id:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        categories=task.categories,
        decision=task.decision,
        scores=task.scores,
        model_versions=task.model_versions,
        created_at=task.created_at,
        completed_at=task.completed_at,
    )
