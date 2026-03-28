from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    AlreadyAssignedError,
    NotFoundError,
    SystemRoleError,
    UniquenessError,
)
from app.models.association import RolePermission, UserRole
from app.models.audit_log import AuditLog
from app.models.role import Permission, Role
from app.models.user import User
from app.schemas.role import PermissionCreate, RoleCreate


async def _write_audit_log(
    db: AsyncSession,
    actor_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    payload: dict[str, Any],
) -> None:
    # 1. Create the audit log entry
    log = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
    )

    # 2. Add the log to the session (commit handled by caller)
    db.add(log)
    # no commit here — caller commits


async def create_role(
    db: AsyncSession,
    data: RoleCreate,
    actor_id: str,  # from JWT payload["sub"]
) -> Role:
    # 1. Check if role already exists
    result = await db.execute(select(Role).where(Role.name == data.name))
    if result.scalar_one_or_none():
        raise UniquenessError("Role name already exists")

    # 2. Create the role
    new_role = Role(name=data.name, description=data.description, created_by=actor_id)
    db.add(new_role)
    await db.flush()  # generates new_role.id without committing

    # 3. Audit log
    await _write_audit_log(
        db,
        actor_id=actor_id,
        action="ROLE_CREATED",
        entity_type="Role",
        entity_id=new_role.id,
        payload={"name": new_role.name, "description": new_role.description},
    )

    await db.flush()
    await db.refresh(new_role)
    return new_role


async def delete_role(db: AsyncSession, role_id: UUID, actor_id: UUID) -> None:
    # 1. Fetch the role
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise NotFoundError("Role not found")

    # 2. Guard: is_system=True → raise error
    if role.is_system:
        raise SystemRoleError("Cannot delete system role")

    # 3. Soft delete
    role.is_deleted = True
    role.deleted_at = datetime.now(timezone.utc)

    # 4. Audit log
    await _write_audit_log(
        db,
        actor_id=actor_id,
        action="ROLE_DELETED",
        entity_type="Role",
        entity_id=role.id,
        payload={"name": role.name},
    )


async def assign_permission(
    db: AsyncSession,
    role_id: UUID,
    data: PermissionCreate,
    actor_id: UUID,
) -> RolePermission:
    result = await db.execute(
        select(Role).where(Role.id == role_id).options(selectinload(Role.permissions))
    )
    role = result.scalar_one_or_none()
    if not role:
        raise NotFoundError("Role not found")

    # 2. Find or create permission
    scope_key = f"{data.resource}:{data.action}"
    result = await db.execute(
        select(Permission).where(Permission.scope_key == scope_key)
    )
    permission = result.scalar_one_or_none()
    if not permission:
        permission = Permission(
            resource=data.resource,
            action=data.action,
            scope_key=scope_key,
        )
        db.add(permission)
        await db.flush()

    # 3. Check not already assigned - query the database directly to avoid stale session data  # noqa: E501
    assoc_result = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role.id,
            RolePermission.permission_id == permission.id,
        )
    )
    existing_assoc = assoc_result.scalar_one_or_none()
    if existing_assoc:
        raise AlreadyAssignedError("Permission already assigned")

    # 4. Create association
    role_perm = RolePermission(
        role_id=role.id,
        permission_id=permission.id,
        granted_by=actor_id,
    )
    db.add(role_perm)
    await db.flush()  # This ensures the record is inserted and gets the server_default values  # noqa: E501
    await db.refresh(role_perm)  # This refreshes the object with the values from the database  # noqa: E501

    # 5. Audit log
    await _write_audit_log(
        db,
        actor_id=actor_id,
        action="PERMISSION_GRANTED",
        entity_type="Role",
        entity_id=role.id,
        payload={"scope_key": scope_key, "role_name": role.name},
    )

    return role_perm


async def revoke_permission(
    db: AsyncSession, role_id: UUID, scope: str, actor_id: UUID
) -> None:
    # 1. Get the role
    result = await db.execute(
        select(Role).where(Role.id == role_id).options(selectinload(Role.permissions))
    )
    role = result.scalar_one_or_none()
    if not role:
        raise NotFoundError("Role not found")

    # 2. Find permission
    result = await db.execute(select(Permission).where(Permission.scope_key == scope))
    permission = result.scalar_one_or_none()
    if not permission:
        raise NotFoundError("Permission not found")

    # 3. Delete association
    await db.execute(
        delete(RolePermission).where(
            RolePermission.role_id == role.id,
            RolePermission.permission_id == permission.id,
        )
    )

    # 4. Audit log
    await _write_audit_log(
        db,
        actor_id=actor_id,
        action="PERMISSION_REVOKED",
        entity_type="Role",
        entity_id=role.id,
        payload={"scope_key": scope, "role_name": role.name},
    )

    return


async def assign_role_to_user(
    db: AsyncSession, user_id: UUID, role_id: UUID, actor_id: UUID
) -> UserRole:
    # 1. Get the user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User not found")

    # 2. Get the role
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise NotFoundError("Role not found")

    # 3. Record the assignment
    user_role = UserRole(user_id=user.id, role_id=role.id, assigned_by=actor_id)
    db.add(user_role)
    await db.flush()  # This ensures the record is inserted and gets the server_default values  # noqa: E501
    await db.refresh(user_role)  # This refreshes the object with the values from the database  # noqa: E501

    # 4. Audit log
    await _write_audit_log(
        db,
        actor_id=actor_id,
        action="USER_ROLE_ASSIGNED",
        entity_type="UserRole",
        entity_id=user.id,
        payload={"user": user.username, "role": role.name},
    )

    return user_role


async def revoke_role_from_user(
    db: AsyncSession, user_id: UUID, role_id: UUID, actor_id: UUID
) -> None:
    # 1. Get the user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User not found")

    # 2. Get the role
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise NotFoundError("Role not found")

    # 3. Revoke the role
    await db.execute(
        delete(UserRole).where(
            UserRole.user_id == user.id,
            UserRole.role_id == role.id,
        )
    )

    # 4. Audit log
    await _write_audit_log(
        db,
        actor_id=actor_id,
        action="USER_ROLE_REVOKED",
        entity_type="UserRole",
        entity_id=user.id,
        payload={"user": user.username, "role": role.name},
    )

    return


async def get_audit_logs(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> list[AuditLog]:
    # 1. Calculate offset based on page and page_size
    offset = (page - 1) * page_size

    # 2. Query to get audit logs with pagination, ordered by created_at descending
    query = (
        select(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)
    audit_logs = result.scalars().all()

    return audit_logs
