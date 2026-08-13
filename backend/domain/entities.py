from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: str
    email: str


@dataclass
class ApiKey:
    id: str
    user_id: str
    name: str
    is_active: bool
    request_limit: int
    created_at: datetime


@dataclass
class ModerationTask:
    id: str
    user_id: str
    status: str
    categories: list[str]
    decision: Optional[str]
    scores: Optional[dict]
    model_versions: Optional[dict]
    created_at: datetime
    completed_at: datetime
