from app.db.session import async_session_factory
from app.rbac.application.use_cases.assign_permission import AssignPermissionUseCase
from app.rbac.application.use_cases.assign_role_to_user import AssignRoleToUserUseCase
from app.rbac.application.use_cases.create_role import CreateRoleUseCase
from app.rbac.application.use_cases.delete_role import DeleteRoleUseCase
from app.rbac.application.use_cases.revoke_permission import RevokePermissionUseCase
from app.rbac.application.use_cases.revoke_role_from_user import (
    RevokeRoleFromUserUseCase,
)
from app.rbac.infrastructure.unit_of_work import SqlAlchemyRbacUnitOfWork


def _uow_factory() -> SqlAlchemyRbacUnitOfWork:
    return SqlAlchemyRbacUnitOfWork(async_session_factory)


def get_create_role_use_case() -> CreateRoleUseCase:
    return CreateRoleUseCase(uow_factory=_uow_factory)


def get_delete_role_use_case() -> DeleteRoleUseCase:
    return DeleteRoleUseCase(uow_factory=_uow_factory)


def get_assign_permission_use_case() -> AssignPermissionUseCase:
    return AssignPermissionUseCase(uow_factory=_uow_factory)


def get_revoke_permission_use_case() -> RevokePermissionUseCase:
    return RevokePermissionUseCase(uow_factory=_uow_factory)


def get_assign_role_to_user_use_case() -> AssignRoleToUserUseCase:
    return AssignRoleToUserUseCase(uow_factory=_uow_factory)


def get_revoke_role_from_user_use_case() -> RevokeRoleFromUserUseCase:
    return RevokeRoleFromUserUseCase(uow_factory=_uow_factory)
