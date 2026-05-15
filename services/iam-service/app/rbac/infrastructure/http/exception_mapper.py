from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.rbac.domain.exceptions import (
    PermissionAlreadyAssignedError,
    PermissionNotFoundError,
    RoleAlreadyExistsError,
    RoleNotFoundError,
    UserNotFoundError,
)
from app.shared.domain.exceptions import SystemRoleProtectedError


def register_rbac_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RoleAlreadyExistsError)
    async def _role_exists(
        request: Request, exc: RoleAlreadyExistsError
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(RoleNotFoundError)
    async def _role_not_found(
        request: Request, exc: RoleNotFoundError
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(SystemRoleProtectedError)
    async def _system_role(
        request: Request, exc: SystemRoleProtectedError
    ) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(PermissionAlreadyAssignedError)
    async def _perm_assigned(
        request: Request, exc: PermissionAlreadyAssignedError
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(PermissionNotFoundError)
    async def _perm_not_found(
        request: Request, exc: PermissionNotFoundError
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(UserNotFoundError)
    async def _user_not_found(
        request: Request, exc: UserNotFoundError
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})
