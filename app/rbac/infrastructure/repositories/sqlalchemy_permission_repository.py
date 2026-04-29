from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rbac.infrastructure.orm.role import Permission as PermissionORM
from app.shared.domain.entities.permission import Permission


def _permission_orm_to_domain(orm: PermissionORM) -> Permission:
    return Permission(
        id=orm.id,
        scope_key=orm.scope_key,
        resource=orm.resource,
        action=orm.action,
    )


class SqlAlchemyPermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_scope_key(self, scope_key: str) -> Permission | None:
        result = await self._session.execute(
            select(PermissionORM).where(PermissionORM.scope_key == scope_key)
        )
        orm = result.scalar_one_or_none()
        return _permission_orm_to_domain(orm) if orm else None

    async def add(
        self, *, resource: str, action: str, scope_key: str
    ) -> Permission:
        orm = PermissionORM(resource=resource, action=action, scope_key=scope_key)
        self._session.add(orm)
        await self._session.flush()
        return _permission_orm_to_domain(orm)
