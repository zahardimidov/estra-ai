from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.config import settings
from infrastructure.db.models import Base

engine = create_async_engine(url=settings.ENGINE, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


async def run_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
