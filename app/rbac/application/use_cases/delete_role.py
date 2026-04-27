from datetime import datetime, timezone

from app.rbac.application.dto import DeleteRoleInput
from app.rbac.domain.exceptions import RoleNotFoundError, SystemRoleProtectedError
from app.rbac.domain.ports.unit_of_work import RbacUnitOfWorkFactory


class DeleteRoleUseCase:
    def __init__(self, uow_factory: RbacUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, input: DeleteRoleInput) -> None:
        async with self._uow_factory() as uow:
            role = await uow.roles.find_by_id(input.role_id)
            if not role:
                raise RoleNotFoundError()
            if role.is_system:
                raise SystemRoleProtectedError()

            now = datetime.now(timezone.utc)
            await uow.roles.mark_deleted(role.id, when=now)

            await uow.audit_logger.log(
                actor_id=input.actor_id,
                action="ROLE_DELETED",
                entity_type="Role",
                entity_id=role.id,
                payload={"name": role.name},
            )

            await uow.commit()
