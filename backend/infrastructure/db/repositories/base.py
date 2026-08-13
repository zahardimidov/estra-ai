from typing import Generic, List, Type, TypeVar

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

M = TypeVar("M")


class BaseRepository(Generic[M]):
    def __init__(self, model: Type[M], session: AsyncSession):
        self.model = model
        self.session = session

    async def create(self, **data) -> M:
        item = self.model(**data)
        self.session.add(item)
        await self.session.flush()  # populate the id before commit
        await self.session.refresh(item)
        return item

    async def get(self, id) -> M | None:
        return await self.session.scalar(select(self.model).where(self.model.id == id))

    async def find(self, limit=None, offset=None, **conditions) -> List[M]:
        stmt = select(self.model).filter_by(**conditions)

        if limit:
            stmt = stmt.limit(limit)
        if offset:
            stmt = stmt.offset(offset)

        result = await self.session.scalars(stmt)
        return result.all()

    async def find_one(self, **conditions) -> M | None:
        stmt = select(self.model).filter_by(**conditions).limit(1)
        return await self.session.scalar(stmt)

    async def get_all(self, limit=None, offset=None) -> List[M]:
        stmt = select(self.model)

        if limit:
            stmt = stmt.limit(limit)
        if offset:
            stmt = stmt.offset(offset)

        result = await self.session.scalars(stmt)
        return result.all()

    async def update(self, id, **updates) -> M | None:
        item = await self.get(id)
        if not item:
            return None

        for k, v in updates.items():
            setattr(item, k, v)

        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def delete(self, id) -> None:
        await self.session.execute(delete(self.model).where(self.model.id == id))
