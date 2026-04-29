from app.rbac.application.dto import CreateRoleInput, CreateRoleResult
from app.rbac.domain.events import RoleCreated
from app.rbac.domain.exceptions import RoleAlreadyExistsError
from app.rbac.domain.ports.unit_of_work import RbacUnitOfWorkFactory


class CreateRoleUseCase:
    def __init__(self, uow_factory: RbacUnitOfWorkFactory) -> None:
        self._uow_factory = uow_factory

    async def execute(self, input: CreateRoleInput) -> CreateRoleResult:
        async with self._uow_factory() as uow:
            if await uow.roles.find_by_name(input.name):
                raise RoleAlreadyExistsError()

            role = await uow.roles.add(
                name=input.name,
                description=input.description,
                created_by=input.actor_id,
            )

            # Emit domain event for audit logging (decoupled via UoW)
            uow.add_event(
                RoleCreated(
                    actor_id=input.actor_id,
                    role_id=role.id,
                    name=role.name,
                    description=role.description,
                    is_system=role.is_system,
                )
            )

            await uow.commit()

        return CreateRoleResult(
            id=role.id,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            created_by=role.created_by,
            created_at=role.created_at,
        )
