""" """

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.association import RolePermission, UserRole
from app.models.audit_log import AuditLog
from app.models.role import Permission, Role
from app.schemas.role import PermissionCreate, RoleCreate


async def _write_audit_log(
    db: AsyncSession,
    actor_id: str,
    action: str,
    entity_type: str,
    entity_id: str,
    payload: dict,
) -> None:
    log = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
    )
    db.add(log)
    # no commit here — caller commits


async def create_role(
    db: AsyncSession,
    data: RoleCreate,
    actor_id: str,  # from JWT payload["sub"]
) -> Role:
    result = await db.execute(select(Role).where(Role.name == data.name))
    if result.scalar_one_or_none():
        raise ValueError("Role name already exists")
    new_role = Role(name=data.name, description=data.description, created_by=actor_id)
    db.add(new_role)
    await db.flush()  # generates new_role.id without committing
    await _write_audit_log(
        db,
        actor_id=actor_id,
        action="ROLE_CREATED",
        entity_type="Role",
        entity_id=new_role.id,
        payload={"name": new_role.name, "description": new_role.description},
    )
    await db.commit()
    await db.refresh(new_role)
    return new_role


async def delete_role(db: AsyncSession, role_id: str, actor_id: str) -> None:
    # 1. Fetch the role
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise ValueError("Role not found")

    # 2. Guard: is_system=True → raise error
    if role.is_system:
        raise PermissionError("Cannot delete system role")
    
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
    await db.commit()


async def assign_permission(
    db: AsyncSession,
    role_id: str,
    data: PermissionCreate,
    actor_id: str,
) -> RolePermission:
    result = await db.execute(
        select(Role).where(Role.id == role_id).options(selectinload(Role.permissions))
    )
    role = result.scalar_one_or_none()
    if not role:
        raise ValueError("Role not found")

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
    
    # 3. Check not laready assigned
    already_assigned = any(p.id == permission.id for p in role.permissions)
    if already_assigned:
        raise ValueError("Permission already assigned")
    
    # 4. Create association
    role_perm = RolePermission(
        role_id=role.id,
        permission_id=permission.id,
        granted_by=actor_id,
    )
    db.add(role_perm)

    # 5. Audit log
    await _write_audit_log(
        db,
        actor_id=actor_id,
        action="PERMISSION_GRANTED",
        entity_type="Role",
        entity_id=role.id,
        payload={"scope_key": scope_key, "role_name": role.name},
    )

    await db.commit()
    return role_perm


async def revoke_permission(
    db: AsyncSession, role_id: str, scope: str, actor_id: str
) -> None:
    # YOUR TURN
    pass


async def assign_role_to_user(
    db: AsyncSession, user_id: str, role_id: str, actor_id: str
) -> UserRole:
    # YOUR TURN
    pass


async def revoke_role_from_user(
    db: AsyncSession, user_id: str, role_id: str, actor_id: str
) -> None:
    # YOUR TURN
    pass


async def get_audit_logs(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> list[AuditLog]:
    # YOUR TURN
    pass
