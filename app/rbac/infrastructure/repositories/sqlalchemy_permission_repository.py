from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.infrastructure.repositories.mappers import _permission_orm_to_domain
from app.rbac.infrastructure.orm.role import Permission as PermissionORM
from app.shared.domain.entities.permission import Permission
from app.shared.domain.values.scope_key import ScopeKey


class SqlAlchemyPermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_scope_key(self, scope_key: ScopeKey) -> Permission | None:
        result = await self._session.execute(
            select(PermissionORM).where(PermissionORM.scope_key == scope_key.key)
        )
        orm = result.scalar_one_or_none()
        return _permission_orm_to_domain(orm) if orm else None

    async def add(self, scope_key: ScopeKey) -> Permission:
        orm = PermissionORM(
            resource=scope_key.resource,
            action=scope_key.action,
            scope_key=scope_key.key,
        )
        self._session.add(orm)
        await self._session.flush()
        return _permission_orm_to_domain(orm)
