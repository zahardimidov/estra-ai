from typing import Optional

from core.security import generate_api_key, hash_api_key
from domain.entities import ApiKey, User
from infrastructure.db.uow import SqlAlchemyUnitOfWork


def _to_entity(row) -> ApiKey:
    return ApiKey(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        is_active=row.is_active,
        request_limit=row.request_limit,
        created_at=row.created_at,
    )


class ApiKeyService:
    def __init__(self, uow: SqlAlchemyUnitOfWork):
        self.uow = uow

    async def create_key(
        self, user_id: str, name: str, request_limit: int = 1000
    ) -> tuple[ApiKey, str]:
        """
        Create a new API key.
        Returns (entity, raw_key). The raw key is shown once — only its hash is stored.
        """
        raw_key = generate_api_key()
        key_hash = hash_api_key(raw_key)

        async with self.uow as uow:
            row = await uow.api_keys.create(
                user_id=user_id,
                name=name,
                key_hash=key_hash,
                request_limit=request_limit,
            )

        return _to_entity(row), raw_key

    async def list_keys(self, user_id: str) -> list[ApiKey]:
        async with self.uow as uow:
            rows = await uow.api_keys.find(user_id=user_id)
        return [_to_entity(r) for r in rows]

    async def delete_key(self, user_id: str, key_id: str) -> bool:
        """Delete key only if it belongs to the requesting user."""
        async with self.uow as uow:
            row = await uow.api_keys.get(key_id)
            if row is None or row.user_id != user_id:
                return False
            await uow.api_keys.delete(key_id)
        return True

    async def get_user_by_raw_key(self, raw_key: str) -> Optional[User]:
        """Validate a raw API key and return the owning user, or None."""
        key_hash = hash_api_key(raw_key)
        async with self.uow as uow:
            row = await uow.api_keys.find_by_hash(key_hash)
            if row is None:
                return None
            user_row = await uow.users.get(row.user_id)

        if user_row is None:
            return None
        return User(id=user_row.id, email=user_row.email)

    async def get_key_by_raw_key(self, raw_key: str) -> Optional[ApiKey]:
        """Validate a raw API key and return the key entity (with request_limit), or None."""
        key_hash = hash_api_key(raw_key)
        async with self.uow as uow:
            row = await uow.api_keys.find_by_hash(key_hash)
        if row is None:
            return None
        return _to_entity(row)
