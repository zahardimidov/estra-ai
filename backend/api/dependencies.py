from typing import Annotated, Optional, Type, TypeVar

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.config import settings
from core.rate_limit import RateLimiter
from core.security import verify_jwt_token
from domain.entities import User
from domain.services import ModerationService, UserService
from domain.services.api_key import ApiKeyService
from infrastructure.db.session import async_session
from infrastructure.db.uow import SqlAlchemyUnitOfWork
from infrastructure.redis.client import redis_client
from infrastructure.redis.queue import TaskQueue
from infrastructure.storage.s3_client import S3Client

T = TypeVar("T")

# auto_error=False — don't auto-raise 403, we handle the error ourselves below
auth_scheme = HTTPBearer(auto_error=False)


def get_uow() -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(async_session)


def get_task_queue() -> TaskQueue:
    return TaskQueue(redis_client)


def get_s3_client() -> S3Client:
    return S3Client(
        endpoint_url=settings.MINIO_URL,
        access_key=settings.MINIO_ROOT_USER,
        secret_key=settings.MINIO_ROOT_PASSWORD,
    )


def get_moderation_service(
    uow=Depends(get_uow),
    queue: TaskQueue = Depends(get_task_queue),
    s3: S3Client = Depends(get_s3_client),
) -> ModerationService:
    return ModerationService(uow, queue, s3)


def get_service(service_class: Type[T]):
    def _factory(uow=Depends(get_uow)) -> T:
        return service_class(uow)

    return _factory


def get_rate_limiter() -> RateLimiter:
    return RateLimiter(redis_client)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(auth_scheme),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    user_service: UserService = Depends(get_service(UserService)),
    api_key_service: ApiKeyService = Depends(get_service(ApiKeyService)),
) -> User:
    if x_api_key:
        user = await api_key_service.get_user_by_raw_key(x_api_key)
        if user:
            return user
        raise HTTPException(status_code=401, detail="Invalid API key.")

    if credentials:
        decoded_data = verify_jwt_token(credentials.credentials)
        if decoded_data:
            jwt_id = decoded_data.get("jwt_id")
            if jwt_id:
                user = await user_service.get_one_by_jwt_id(jwt_id)
                if user:
                    return user
        raise HTTPException(status_code=401, detail="Invalid or expired token.")

    raise HTTPException(status_code=403, detail="Not authenticated.")


async def enforce_rate_limit(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    api_key_service: ApiKeyService = Depends(get_service(ApiKeyService)),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    """No-op for JWT-authenticated requests — only API keys carry a request_limit.
    An invalid key is left for get_current_user to reject with 401."""
    if not x_api_key:
        return
    api_key = await api_key_service.get_key_by_raw_key(x_api_key)
    if api_key is None:
        return
    allowed = await limiter.check_and_increment(api_key.id, api_key.request_limit)
    if not allowed:
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")


CurrentUser = Annotated[User, Depends(get_current_user)]
