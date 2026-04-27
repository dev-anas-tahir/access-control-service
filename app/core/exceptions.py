"""
Cross-cutting exceptions used by JWT verification.

Domain-specific errors live in their respective bounded contexts under
`app/<context>/domain/exceptions.py`.
"""


class TokenExpiredError(Exception):
    """Raised when a JWT token has expired."""


class InvalidTokenError(Exception):
    """Raised when a JWT token is invalid or malformed."""
