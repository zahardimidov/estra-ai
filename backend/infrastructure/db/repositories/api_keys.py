from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import ApiKey
from infrastructure.db.repositories.base import BaseRepository


class ApiKeyRepository(BaseRepository[ApiKey]):
    def __init__(self, session: AsyncSession):
        super().__init__(ApiKey, session)

    async def find_by_hash(self, key_hash: str) -> ApiKey | None:
        return await self.find_one(key_hash=key_hash, is_active=True)
