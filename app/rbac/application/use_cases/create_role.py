from app.rbac.application.dto import CreateRoleInput, CreateRoleResult
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

            await uow.audit_logger.log(
                actor_id=input.actor_id,
                action="ROLE_CREATED",
                entity_type="Role",
                entity_id=role.id,
                payload={"name": role.name, "description": role.description},
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
