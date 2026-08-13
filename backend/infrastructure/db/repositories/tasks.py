from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import ModerationTask
from infrastructure.db.repositories.base import BaseRepository


class ModerationTaskRepository(BaseRepository[ModerationTask]):
    def __init__(self, session: AsyncSession):
        super().__init__(ModerationTask, session)

    async def update_status(
        self,
        task_id: str,
        status: str,
        decision: str | None = None,
        scores_json: dict | None = None,
        model_versions_used: dict | None = None,
    ) -> ModerationTask | None:
        updates = {"status": status}
        if decision is not None:
            updates["decision"] = decision
        if scores_json is not None:
            updates["scores_json"] = scores_json
        if model_versions_used is not None:
            updates["model_versions_used"] = model_versions_used
        return await self.update(task_id, **updates)
