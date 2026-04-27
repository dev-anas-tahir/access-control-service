from app.models.role import Permission as PermissionORM
from app.models.role import Role as RoleORM
from app.models.user import User as UserORM
from app.shared.domain.entities.permission import Permission
from app.shared.domain.entities.role import Role
from app.shared.domain.entities.user import User


def _permission_orm_to_domain(orm: PermissionORM) -> Permission:
    return Permission(
        id=orm.id,
        scope_key=orm.scope_key,
        resource=orm.resource,
        action=orm.action,
    )


def _role_orm_to_domain(orm: RoleORM) -> Role:
    return Role(
        id=orm.id,
        name=orm.name,
        permissions=[_permission_orm_to_domain(p) for p in orm.permissions],
    )


def user_orm_to_domain(orm: UserORM) -> User:
    return User(
        id=orm.id,
        username=orm.username,
        email=orm.email,
        password_hash=orm.password_hash,
        is_active=orm.is_active,
        is_super_user=orm.is_super_user,
        organization_id=orm.organization_id,
        roles=[_role_orm_to_domain(r) for r in orm.roles],
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


def apply_domain_to_user_orm(domain: User, orm: UserORM) -> None:
    """Mutate an existing ORM instance with updated domain fields."""
    orm.username = domain.username
    orm.email = domain.email
    orm.password_hash = domain.password_hash
    orm.is_active = domain.is_active
    orm.is_super_user = domain.is_super_user
