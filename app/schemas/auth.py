"""Schemas for authentication-related requests and responses.

This module contains Pydantic models for handling authentication-related data
structures including signup, login, token management, and user information.

The schemas are designed to:
- Validate incoming data
- Serialize outgoing data
- Provide clear documentation for API endpoints
- Enforce data integrity

Example:
    ```python
    from app.schemas.auth import SignupRequest

    # Create a signup request
    signup_data = SignupRequest(
        username="john_doe",
        password="SecurePass123!",
        email="john@example.com"
    )
    ```
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
    """Request schema for user signup."""

    username: str = Field(min_length=3, max_length=50)
    password: str
    email: EmailStr | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """
        Validate password strength.

        Password must meet the following criteria:
        - At least 8 characters long
        - Contains at least one uppercase letter
        - Contains at least one digit
        - Contains at least one special character from: !@#$%^&*()_+-=[]{}|;':",<>,./?

        Args:
            v: The password string to validate.

        Returns:
            The validated password string.

        Raises:
            ValueError: If the password does not meet the minimum strength requirements.

        Example:
            ```python
            # Valid password
            password = "MyPassword123!"

            # Invalid password (missing special character)
            # password = "MyPassword123"  # Would raise ValueError
            ```
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;':\"<>,.?/" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class LoginRequest(BaseModel):
    """
    Request schema for user login.

    Used to authenticate a user with their username and password.

    Attributes:
        username: The user's username.
        password: The user's password.
    """

    username: str
    password: str


class TokenResponse(BaseModel):
    """
    Response schema for authentication tokens.

    Used to return authentication tokens to the client after successful login.

    Attributes:
        access_token: The JWT access token for authentication.
        token_type: The type of token (defaults to "bearer").
    """

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """
    Response schema for user information.

    Used to serialize user data for API responses.

    Attributes:
        id: The user's unique identifier.
        username: The user's username.
        email: The user's email address (optional).
        created_at: The timestamp when the user was created.
    """

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    username: str
    email: EmailStr | None = None
    created_at: datetime


class MeResponse(BaseModel):
    """
    Response schema for the authenticated user's information,
    including roles and permissions.

    Used to return detailed user information including their roles and
    associated permissions for the authenticated user.

    Attributes:
        id: The user's unique identifier.
        username: The user's username.
        email: The user's email address (optional).
        roles: List of role names assigned to the user.
        permissions: List of permission scope keys available to the user.
        is_super_user: Flag indicating if the user has super user privileges.
        created_at: The timestamp when the user was created.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str | None = None
    roles: list[str]
    permissions: list[str]
    is_super_user: bool
