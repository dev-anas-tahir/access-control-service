"""Schemas for authentication-related requests and responses."""

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
        Check length, one uppercase one digit, and one special character.
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
    """Request schema for user login."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Response schema for authentication tokens."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Response schema for user information."""

    model_config = ConfigDict(from_attributes=True)
    id: UUID
    username: str
    email: EmailStr | None = None
    created_at: datetime


class MeResponse(BaseModel):
    """
    Response schema for the authenticated user's information,
    including roles and permissions.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: str | None = None
    roles: list[str]
    permissions: list[str]
    is_super_user: bool
    created_at: datetime
