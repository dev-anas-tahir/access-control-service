from fastapi import FastAPI

from app.rbac.domain.exceptions import (
    PermissionAlreadyAssignedError,
    PermissionNotFoundError,
    RoleAlreadyExistsError,
    RoleNotFoundError,
    UserNotFoundError,
)
from app.shared.domain.exceptions import SystemRoleProtectedError
from app.shared.infrastructure.http.exception_utils import register_exception_handlers


def register_rbac_exception_handlers(app: FastAPI) -> None:
    register_exception_handlers(
        app,
        {
            RoleAlreadyExistsError: 409,
            RoleNotFoundError: 404,
            SystemRoleProtectedError: 403,
            PermissionAlreadyAssignedError: 409,
            PermissionNotFoundError: 404,
            UserNotFoundError: 404,
        },
    )
