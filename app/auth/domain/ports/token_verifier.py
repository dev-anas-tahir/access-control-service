from typing import Protocol


class TokenVerifier(Protocol):
    """Verifies a signed access token and returns the decoded payload.

    Raises InvalidCredentialsError-compatible exceptions on failure; callers
    should catch them and map to HTTP 401.
    """

    def verify(self, token: str) -> dict[str, object]: ...
