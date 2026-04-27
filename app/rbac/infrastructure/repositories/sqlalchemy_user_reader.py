import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User as UserORM
from app.rbac.domain.ports.user_reader import UserSummary


class SqlAlchemyUserReader:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_summary_by_id(self, id: uuid.UUID) -> UserSummary | None:
        result = await self._session.execute(
            select(UserORM.id, UserORM.username).where(UserORM.id == id)
        )
        row = result.first()
        return UserSummary(id=row.id, username=row.username) if row else None
