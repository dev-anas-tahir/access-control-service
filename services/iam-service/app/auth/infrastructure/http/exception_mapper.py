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
from app.shared.infrastructure.http.exception_utils import register_exception_handlers


def register_auth_exception_handlers(app: FastAPI) -> None:
    register_exception_handlers(
        app,
        {
            InvalidCredentialsError: 401,
            RefreshTokenInvalidError: 401,
            UserExistsError: 409,
            DefaultRoleMissingError: 500,
        },
    )

    @app.exception_handler(TokenExpiredError)
    async def _token_expired(request: Request, exc: TokenExpiredError) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"detail": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(InvalidTokenError)
    async def _invalid_token(request: Request, exc: InvalidTokenError) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"detail": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        )
