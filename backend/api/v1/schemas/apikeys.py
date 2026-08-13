from datetime import datetime

from api.v1.schemas.base import BaseModel, PydanticBaseModel


class ApiKeyCreateRequest(BaseModel):
    name: str
    request_limit: int = 1000


class ApiKeyCreateResponse(PydanticBaseModel):
    """Returned once on creation — includes the raw key."""
    id: str
    name: str
    key: str          # raw key, shown only once
    request_limit: int
    created_at: datetime


class ApiKeyResponse(PydanticBaseModel):
    """Safe representation — no raw key."""
    id: str
    name: str
    is_active: bool
    request_limit: int
    created_at: datetime
