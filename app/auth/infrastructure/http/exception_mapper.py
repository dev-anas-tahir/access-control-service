from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.auth.domain.exceptions import (
    DefaultRoleMissingError,
    InvalidCredentialsError,
    InvalidTokenError,
    RefreshTokenInvalidError,
    TokenExpiredError,
    UserExistsError,
)


def register_auth_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidCredentialsError)
    async def _invalid_credentials(
        request: Request, exc: InvalidCredentialsError
    ) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(RefreshTokenInvalidError)
    async def _refresh_token_invalid(
        request: Request, exc: RefreshTokenInvalidError
    ) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc)})

    @app.exception_handler(UserExistsError)
    async def _user_exists(request: Request, exc: UserExistsError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(DefaultRoleMissingError)
    async def _default_role_missing(
        request: Request, exc: DefaultRoleMissingError
    ) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(exc)})

    @app.exception_handler(TokenExpiredError)
    async def _token_expired(
        request: Request, exc: TokenExpiredError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"detail": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(InvalidTokenError)
    async def _invalid_token(
        request: Request, exc: InvalidTokenError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"detail": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        )
