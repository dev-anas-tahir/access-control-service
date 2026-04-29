from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.infrastructure.repositories.mappers import _role_orm_to_domain
from app.rbac.infrastructure.orm.role import Role as RoleORM
from app.shared.domain.entities.role import Role


class SqlAlchemyRoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_name(self, name: str) -> Role | None:
        result = await self._session.execute(
            select(RoleORM)
            .where(RoleORM.name == name)
            .options(selectinload(RoleORM.permissions))
        )
        orm = result.scalar_one_or_none()
        return _role_orm_to_domain(orm) if orm else None
