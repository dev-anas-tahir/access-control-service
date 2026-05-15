from typing import Protocol, TypedDict


class TokenPayload(TypedDict):
    """Decoded JWT claims emitted by TokenVerifier.

    Mirrors the schema produced by JwtTokenIssuer.issue() so that downstream
    consumers (HTTP dependencies, route handlers) can rely on a stable shape.
    """

    sub: str
    iss: str
    iat: float
    exp: float
    jti: str
    username: str
    roles: list[str]
    permissions: list[str]
    is_super_user: bool


class TokenVerifier(Protocol):
    """Verifies a signed access token and returns the decoded payload.

    Raises InvalidTokenError or TokenExpiredError on failure; callers should
    catch them and map to HTTP 401.
    """

    def verify(self, token: str) -> TokenPayload: ...
