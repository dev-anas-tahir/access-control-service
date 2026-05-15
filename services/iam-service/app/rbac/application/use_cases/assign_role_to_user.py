from app.rbac.application.dto import (
    AssignRoleToUserInput,
    AssignRoleToUserResult,
)
from app.rbac.domain.events import UserRoleAssigned
from app.rbac.domain.exceptions import RoleNotFoundError, UserNotFoundError
from app.rbac.domain.ports.unit_of_work import RbacUnitOfWorkFactory


class AssignRoleToUserUseCase:
    def __init__(self, uow_factory: RbacUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(
        self, input: AssignRoleToUserInput
    ) -> AssignRoleToUserResult:
        async with self._uow_factory() as uow:
            user = await uow.users.find_summary_by_id(input.user_id)
            if not user:
                raise UserNotFoundError()

            role = await uow.roles.find_by_id(input.role_id)
            if not role:
                raise RoleNotFoundError()

            await uow.assignments.assign_role_to_user(
                user_id=user.id, role_id=role.id, assigned_by=input.actor_id
            )

            # Emit domain event for audit logging (decoupled via UoW)
            uow.add_event(
                UserRoleAssigned(
                    actor_id=input.actor_id,
                    user_id=user.id,
                    user_name=user.username,
                    role_id=role.id,
                    role_name=role.name,
                )
            )

            await uow.commit()

        return AssignRoleToUserResult(user_id=user.id, role_id=role.id)
