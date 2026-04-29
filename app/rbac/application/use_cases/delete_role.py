from datetime import datetime, timezone

from app.rbac.application.dto import DeleteRoleInput
from app.rbac.domain.events import RoleDeleted
from app.rbac.domain.exceptions import RoleNotFoundError
from app.rbac.domain.ports.unit_of_work import RbacUnitOfWorkFactory


class DeleteRoleUseCase:
    def __init__(self, uow_factory: RbacUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, input: DeleteRoleInput) -> None:
        async with self._uow_factory() as uow:
            role = await uow.roles.find_by_id(input.role_id)
            if not role:
                raise RoleNotFoundError()

            role.assert_deletable()

            now = datetime.now(timezone.utc)
            await uow.roles.mark_deleted(role.id, when=now)

            # Emit domain event for audit logging (decoupled via UoW)
            uow.add_event(
                RoleDeleted(
                    actor_id=input.actor_id,
                    role_id=role.id,
                    name=role.name,
                )
            )

            await uow.commit()
