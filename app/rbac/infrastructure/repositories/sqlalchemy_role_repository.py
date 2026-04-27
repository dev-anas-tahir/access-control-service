import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.infrastructure.repositories.mappers import _role_orm_to_domain
from app.models.role import Role as RoleORM
from app.shared.domain.entities.role import Role


class SqlAlchemyRoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, id: uuid.UUID) -> Role | None:
        result = await self._session.execute(
            select(RoleORM)
            .where(RoleORM.id == id)
            .options(selectinload(RoleORM.permissions))
        )
        orm = result.scalar_one_or_none()
        return _role_orm_to_domain(orm) if orm else None

    async def find_by_name(self, name: str) -> Role | None:
        result = await self._session.execute(
            select(RoleORM)
            .where(RoleORM.name == name)
            .options(selectinload(RoleORM.permissions))
        )
        orm = result.scalar_one_or_none()
        return _role_orm_to_domain(orm) if orm else None

    async def add(
        self,
        *,
        name: str,
        description: str | None,
        created_by: uuid.UUID,
    ) -> Role:
        orm = RoleORM(name=name, description=description, created_by=created_by)
        self._session.add(orm)
        await self._session.flush()
        await self._session.refresh(orm, ["permissions"])
        return _role_orm_to_domain(orm)

    async def mark_deleted(self, id: uuid.UUID, when: datetime) -> None:
        result = await self._session.execute(select(RoleORM).where(RoleORM.id == id))
        orm = result.scalar_one()
        orm.is_deleted = True
        orm.deleted_at = when
        self._session.add(orm)
