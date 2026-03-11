"""
This module defines the authentication API endpoints for user registration, login,
token refresh, logout, and retrieving current user information. It uses FastAPI's
APIRouter to organize the routes under the "/auth" prefix and includes appropriate
request and response models for each endpoint.
"""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.exceptions import UniquenessError
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    MeResponse,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_SETTINGS = {
    "key": "refresh_token",
    "httponly": True,
    "secure": True,
    "samesite": "lax",
    "max_age": 7 * 24 * 3600,
}


@router.post(
    "/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def signup(data: SignupRequest, db: AsyncSession = Depends(get_db)):
    """
    Endpoint for user registration. It accepts a SignupRequest, creates a new user,
    and returns the user's information.
    Args:
        data (SignupRequest): The signup request data.
        db (AsyncSession): The database session.

    Returns:
        UserResponse: The response containing the created user's information.
    Raises:
        HTTPException: If the username or email is already taken (409 Conflict) or
        if there is an internal server error (500).
    """
    try:
        user = await auth_service.signup(db, data)
        return UserResponse.model_validate(user)
    except UniquenessError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)
):
    """
    Endpoint for user login. It accepts a LoginRequest, verifies the user's credentials,
    and returns an access token. The refresh token is set as an HTTP-only cookie.
    Args:
        data (LoginRequest): The login request data.
        response (Response): The FastAPI Response object to set cookies.
        db (AsyncSession): The database session.
    Returns:
        TokenResponse: The response containing the access token.
    Raises:
        HTTPException: If the credentials are invalid (401 Unauthorized)
        or if there is an internal server error (500).
    """
    try:
        access_token, refresh_token = await auth_service.login(db, data)
        response.set_cookie(
            value=refresh_token, **COOKIE_SETTINGS
        )
        return TokenResponse(access_token=access_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token: str = Cookie(...),
):
    """
    Endpoint to refresh the access token using a valid refresh token. The new access token
    is returned in the response body, and a new refresh token is set as an HTTP-only cookie.
    Args:
        response (Response): The FastAPI Response object to set cookies.
        db (AsyncSession): The database session.
        refresh_token (str): The refresh token extracted from the cookie.
    Returns:
        TokenResponse: The response containing the new access token.
    Raises:
        HTTPException: If the refresh token is invalid or expired (401 Unauthorized)
        or if there is an internal server error (500).
    """  # noqa: E501
    try:
        access_token, new_refresh_token = await auth_service.refresh_token(
            db, refresh_token
        )
        response.set_cookie(
            value=new_refresh_token, **COOKIE_SETTINGS
        )
        return TokenResponse(access_token=access_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    payload: dict = Depends(get_current_user),
    refresh_token: str = Cookie(...),
):
    """
    Endpoint to log out a user by invalidating their refresh token.
    It deletes the refresh token from Redis, ensuring it can no longer be used to generate new access tokens.
    It also removes the refresh token cookie from the client's browser.
    Args:
        response (Response): The FastAPI Response object to delete cookies.
        payload (dict): The payload of the access token, provided by the get_current_user dependency.
        refresh_token (str): The refresh token extracted from the cookie.
    Returns:
        Response: A response with status code 204 No Content if logout is successful.
    Raises:
        HTTPException: If there is an internal server error (500).
    """  # noqa: E501
    try:
        await auth_service.logout(refresh_token, payload)
        response.delete_cookie(key="refresh_token")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/me", response_model=MeResponse)
async def me(payload: dict = Depends(get_current_user)):
    """Endpoint to retrieve the current user's information based on the access token.
    It depends on the get_current_user dependency to verify the token and extract the user's information from the payload.
    Args:
        payload (dict): The payload of the access token, provided by the get_current_user dependency.
    Returns:
        MeResponse: The response containing the user's information.
    """  # noqa: E501
    return MeResponse(
        id=payload["sub"],
        username=payload["username"],
        roles=payload["roles"],
        permissions=payload["permissions"],
        is_super_user=payload["is_super_user"],
    )
