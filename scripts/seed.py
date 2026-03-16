import asyncio
import logging

from sqlalchemy import select

from app.db.session import async_session_factory
from app.models.association import RolePermission
from app.models.role import Permission, Role

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_or_create_role(db, name: str, description: str) -> Role:
    # 1. Check if role already exists in the database
    result = await db.execute(select(Role).where(Role.name == name))
    role = result.scalar_one_or_none()

    # 2. If role doesn't exist, create a new one
    if not role:
        role = Role(name=name, description=description, is_system=True)
        db.add(role)
        await db.flush()
        logger.info(f"✅ Created role: {name}")
    else:
        # 3. If role exists, log and continue
        logger.info(f"⏭️  Role already exists: {name}")
    return role


async def get_or_create_permission(db, resource: str, action: str) -> Permission:
    # 1. Generate the scope key from resource and action
    scope_key = f"{resource}:{action}"

    # 2. Check if permission already exists in the database
    result = await db.execute(
        select(Permission).where(Permission.scope_key == scope_key)
    )
    permission = result.scalar_one_or_none()

    # 3. If permission doesn't exist, create a new one
    if not permission:
        permission = Permission(
            resource=resource,
            action=action,
            scope_key=scope_key,
        )
        db.add(permission)
        await db.flush()
        logger.info(f"✅ Created permission: {scope_key}")
    else:
        # 4. If permission exists, log and continue
        logger.info(f"⏭️  Permission already exists: {scope_key}")
    return permission


async def assign_permission_to_role(db, role: Role, permission: Permission) -> None:
    # 1. Check if the permission is already assigned to the role
    result = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role.id,
            RolePermission.permission_id == permission.id,
        )
    )

    # 2. If not already assigned, create the association
    if not result.scalar_one_or_none():
        db.add(RolePermission(role_id=role.id, permission_id=permission.id))
        logger.info(f"✅ Assigned {permission.scope_key} → {role.name}")


async def seed(db) -> None:
    # ──────────── ROLES ──────────── #
    viewer = await get_or_create_role(db, "viewer", "Default read-only role")
    admin = await get_or_create_role(db, "admin", "Full access administrative role")

    # ──────────── PERMISSIONS ──────────── #
    permissions = [
        ("user", "view"),
        ("user", "create"),
        ("user", "update"),
        ("user", "delete"),
        ("role", "view"),
        ("role", "create"),
        ("role", "delete"),
        ("audit", "view"),
    ]

    created_permissions = []
    for resource, action in permissions:
        perm = await get_or_create_permission(db, resource, action)
        created_permissions.append(perm)

    # ──────────── ASSIGN PERMISSIONS TO ROLES ──────────── #
    # viewer gets read-only permissions
    viewer_scopes = {"user:view", "role:view"}
    for perm in created_permissions:
        if perm.scope_key in viewer_scopes:
            await assign_permission_to_role(db, viewer, perm)

    # admin gets everything
    for perm in created_permissions:
        await assign_permission_to_role(db, admin, perm)

    await db.commit()
    logger.info("🎉 Seed completed successfully")


async def main():
    async with async_session_factory() as db:
        try:
            await seed(db)
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Seed failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
