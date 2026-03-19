"""
Custom exceptions for the access control service. These exceptions are used to handle
-specific error cases in the application, such as uniqueness violations during user
signup. By defining custom exceptions, we can provide more meaningful error messages
and handle specific error scenarios in a more granular way.
"""


class UniquenessError(Exception):
    """Custom exception raised when a username is already taken."""

    pass


class NotFoundError(Exception):
    """Raised when a requested resource does not exist."""

    pass


class SystemRoleError(Exception):
    """Raised when attempting to modify a protected system role."""

    pass


class AlreadyAssignedError(Exception):
    """Raised when a role or permission is already assigned."""

    pass


class TokenExpiredError(Exception):
    """Raised when a JWT token has expired."""

    pass


class InvalidTokenError(Exception):
    """Raised when a JWT token is invalid or malformed."""

    pass
