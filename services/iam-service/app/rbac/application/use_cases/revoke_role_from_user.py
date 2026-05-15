from app.rbac.application.dto import RevokeRoleFromUserInput
from app.rbac.domain.events import UserRoleRevoked
from app.rbac.domain.exceptions import RoleNotFoundError, UserNotFoundError
from app.rbac.domain.ports.unit_of_work import RbacUnitOfWorkFactory


class RevokeRoleFromUserUseCase:
    def __init__(self, uow_factory: RbacUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, input: RevokeRoleFromUserInput) -> None:
        async with self._uow_factory() as uow:
            user = await uow.users.find_summary_by_id(input.user_id)
            if not user:
                raise UserNotFoundError()

            role = await uow.roles.find_by_id(input.role_id)
            if not role:
                raise RoleNotFoundError()

            await uow.assignments.revoke_role_from_user(
                user_id=user.id, role_id=role.id
            )

            # Emit domain event for audit logging (decoupled via UoW)
            uow.add_event(
                UserRoleRevoked(
                    actor_id=input.actor_id,
                    user_id=user.id,
                    user_name=user.username,
                    role_id=role.id,
                    role_name=role.name,
                )
            )

            await uow.commit()
