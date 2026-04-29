from fastapi import APIRouter, Cookie, Depends, Response, status

from app.auth.application.use_cases.login import LoginUseCase
from app.auth.application.use_cases.logout import LogoutUseCase
from app.auth.application.use_cases.refresh_token import RefreshTokenUseCase
from app.auth.application.use_cases.signup import SignupUseCase
from app.auth.infrastructure.composition import (
    get_login_use_case,
    get_logout_use_case,
    get_refresh_token_use_case,
    get_signup_use_case,
)
from app.auth.infrastructure.http.dependencies import get_current_user
from app.auth.infrastructure.http.schemas import (
    LoginRequest,
    MeResponse,
    SignupRequest,
    TokenResponse,
    UserResponse,
    make_logout_input,
    make_refresh_input,
)
from app.auth.domain.ports.token_verifier import TokenPayload
from app.config import settings
from app.shared.infrastructure.http.rate_limit import (
    rate_limit_by_ip,
    rate_limit_by_username,
)

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_SETTINGS = {
    "key": "refresh_token",
    "httponly": True,
    "secure": settings.app_env != "development",
    "samesite": "lax",
    "max_age": 7 * 24 * 3600,
}


@router.post(
    "/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def signup(
    data: SignupRequest,
    use_case: SignupUseCase = Depends(get_signup_use_case),
    _ip: None = Depends(rate_limit_by_ip),
) -> UserResponse:
    result = await use_case.execute(data.to_input())
    return UserResponse(
        id=result.id,
        username=result.username,
        email=result.email,  # type: ignore[arg-type]
        created_at=result.created_at,  # type: ignore[arg-type]
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    response: Response,
    use_case: LoginUseCase = Depends(get_login_use_case),
    _ip: None = Depends(rate_limit_by_ip),
    _user: None = Depends(rate_limit_by_username),
) -> TokenResponse:
    result = await use_case.execute(data.to_input())
    response.set_cookie(value=result.refresh_token, **COOKIE_SETTINGS)
    return TokenResponse(access_token=result.access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    refresh_token: str = Cookie(...),
    use_case: RefreshTokenUseCase = Depends(get_refresh_token_use_case),
    _ip: None = Depends(rate_limit_by_ip),
) -> TokenResponse:
    result = await use_case.execute(make_refresh_input(refresh_token))
    response.set_cookie(value=result.refresh_token, **COOKIE_SETTINGS)
    return TokenResponse(access_token=result.access_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: str = Cookie(...),
    payload: TokenPayload = Depends(get_current_user),
    use_case: LogoutUseCase = Depends(get_logout_use_case),
) -> None:
    await use_case.execute(make_logout_input(refresh_token, payload))  # type: ignore[arg-type]
    response.delete_cookie(key="refresh_token")


@router.get("/me", response_model=MeResponse)
async def me(payload: TokenPayload = Depends(get_current_user)) -> MeResponse:
    return MeResponse(
        id=payload["sub"],  # type: ignore[arg-type]
        username=payload["username"],  # type: ignore[arg-type]
        roles=payload["roles"],  # type: ignore[arg-type]
        permissions=payload["permissions"],  # type: ignore[arg-type]
        is_super_user=payload["is_super_user"],  # type: ignore[arg-type]
    )
