import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.rbac.infrastructure.orm.association import RolePermission, UserRole


class SqlAlchemyAssignmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Role ↔ Permission ────────────────────────────────────────────────────
    async def role_has_permission(
        self, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> bool:
        result = await self._session.execute(
            select(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def assign_permission(
        self,
        role_id: uuid.UUID,
        permission_id: uuid.UUID,
        granted_by: uuid.UUID,
    ) -> None:
        assoc = RolePermission(
            role_id=role_id, permission_id=permission_id, granted_by=granted_by
        )
        self._session.add(assoc)
        await self._session.flush()

    async def revoke_permission(
        self, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> None:
        await self._session.execute(
            delete(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == permission_id,
            )
        )

    # ── User ↔ Role ──────────────────────────────────────────────────────────
    async def assign_role_to_user(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by: uuid.UUID,
    ) -> None:
        assoc = UserRole(user_id=user_id, role_id=role_id, assigned_by=assigned_by)
        self._session.add(assoc)
        await self._session.flush()

    async def revoke_role_from_user(
        self, user_id: uuid.UUID, role_id: uuid.UUID
    ) -> None:
        await self._session.execute(
            delete(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id,
            )
        )
