"""This module defines dependencies for FastAPI routes, such as authentication and
authorization checks."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import verify_access_token
from app.core.types import TokenPayload
from app.db.redis import redis_client

http_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
) -> TokenPayload:
    """
    Dependency to get the current user from the access token. It verifies the token
    and checks if it has been revoked.
    Args:
        token (str): The access token extracted from the Authorization header.
    Returns:
        TokenPayload: The payload of the access token if valid and not revoked.
    Raises:
        HTTPException: If the token is invalid or has been revoked.
    """
    token = credentials.credentials
    try:
        payload = verify_access_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    is_revoked = await redis_client.get(f"revoked_jti:{payload['jti']}")
    if is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def require_super_user(
    payload: TokenPayload = Depends(get_current_user),
) -> TokenPayload:
    """
    Dependency to check if the current user has super user privileges. It depends on
    the get_current_user dependency to first verify the user's identity.
    Args:
        payload (dict): The payload of the access token, provided by the
        get_current_user dependency.
    Returns:
        TokenPayload: The payload of the access token if the user has super user privileges.
    Raises:
        HTTPException: If the user does not have super user privileges.
    """  # noqa: E501
    if not payload.get("is_super_user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Super user privileges required.",
        )
    return payload
