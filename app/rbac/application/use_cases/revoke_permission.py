from app.rbac.application.dto import RevokePermissionInput
from app.rbac.domain.exceptions import (
    PermissionNotFoundError,
    RoleNotFoundError,
)
from app.rbac.domain.ports.unit_of_work import RbacUnitOfWorkFactory
from app.shared.domain.values.scope_key import ScopeKey


class RevokePermissionUseCase:
    def __init__(self, uow_factory: RbacUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, input: RevokePermissionInput) -> None:
        async with self._uow_factory() as uow:
            role = await uow.roles.find_by_id(input.role_id)
            if not role:
                raise RoleNotFoundError()

            scope_key = ScopeKey.parse(input.scope_key)
            permission = await uow.permissions.find_by_scope_key(scope_key)
            if not permission:
                raise PermissionNotFoundError()

            await uow.assignments.revoke_permission(
                role_id=role.id, permission_id=permission.id
            )

            await uow.audit_logger.log(
                actor_id=input.actor_id,
                action="PERMISSION_REVOKED",
                entity_type="Role",
                entity_id=role.id,
                payload={"scope_key": scope_key.key, "role_name": role.name},
            )

            await uow.commit()
