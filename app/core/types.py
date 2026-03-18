"""Custom type definitions for the application"""

from typing import TypedDict


class TokenPayload(TypedDict):
    """TypedDict for the JWT payload structure."""
    sub: str
    iss: str
    iat: float
    exp: float
    jti: str
    username: str
    roles: list[str]
    permissions: list[str]
    is_super_user: bool
