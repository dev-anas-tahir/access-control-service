from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.shared.infrastructure.http.jwks import jwks_client

http_bearer = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(http_bearer),
) -> dict:
    try:
        return jwks_client.verify(credentials.credentials)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_catalog_write(
    payload: dict = Depends(get_current_user),
) -> dict:
    permissions: list[str] = payload.get("permissions", [])
    if "catalog:write" not in permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="catalog:write permission required",
        )
    return payload
