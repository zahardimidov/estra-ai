from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import AnyHttpUrl

from api.v1.schemas.base import BaseModel, PydanticBaseModel


class ModerationCategory(str, Enum):
    toxicity = "toxicity"
    spam = "spam"
    scam = "scam"
    nsfw = "nsfw"


class ModerateTextRequest(BaseModel):
    text: str
    categories: list[ModerationCategory] = [
        ModerationCategory.spam,
        ModerationCategory.toxicity,
        ModerationCategory.scam,
    ]
    callback_url: Optional[AnyHttpUrl] = None


class ModerateResponse(PydanticBaseModel):
    task_id: str
    status: str


class TaskStatusResponse(PydanticBaseModel):
    task_id: str
    status: str
    categories: list[str]
    decision: Optional[str] = None
    scores: Optional[dict] = None
    model_versions: Optional[dict] = None
    created_at: datetime
    completed_at: datetime
