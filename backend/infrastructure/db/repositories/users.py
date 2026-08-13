from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import User
from infrastructure.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)
