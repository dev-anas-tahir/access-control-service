"""
Custom exceptions for the access control service. These exceptions are used to handle
specific error cases in the application, such as uniqueness violations during user
signup. By defining custom exceptions, we can provide more meaningful error messages
and handle specific error scenarios in a more granular way.
"""


class UniquenessError(Exception):
    """Custom exception raised when a username is already taken."""

    pass
