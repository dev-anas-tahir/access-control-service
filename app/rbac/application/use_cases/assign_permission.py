from app.rbac.application.dto import AssignPermissionInput, AssignPermissionResult
from app.rbac.domain.exceptions import (
    PermissionAlreadyAssignedError,
    RoleNotFoundError,
)
from app.rbac.domain.ports.unit_of_work import RbacUnitOfWorkFactory
from app.shared.domain.values.scope_key import ScopeKey


class AssignPermissionUseCase:
    def __init__(self, uow_factory: RbacUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, input: AssignPermissionInput) -> AssignPermissionResult:
        async with self._uow_factory() as uow:
            role = await uow.roles.find_by_id(input.role_id)
            if not role:
                raise RoleNotFoundError()

            scope_key = ScopeKey(resource=input.resource, action=input.action)
            permission = await uow.permissions.find_by_scope_key(scope_key)
            if not permission:
                permission = await uow.permissions.add(scope_key)

            if await uow.assignments.role_has_permission(role.id, permission.id):
                raise PermissionAlreadyAssignedError()

            await uow.assignments.assign_permission(
                role_id=role.id,
                permission_id=permission.id,
                granted_by=input.actor_id,
            )

            await uow.audit_logger.log(
                actor_id=input.actor_id,
                action="PERMISSION_GRANTED",
                entity_type="Role",
                entity_id=role.id,
                payload={"scope_key": scope_key.key, "role_name": role.name},
            )

            await uow.commit()

        return AssignPermissionResult(role_id=role.id, permission_id=permission.id)
