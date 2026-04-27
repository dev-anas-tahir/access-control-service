from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.auth.application.dto import (
    LoginInput,
    LogoutInput,
    RefreshInput,
    SignupInput,
)


class SignupRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(min_length=3, max_length=50)
    password: str
    email: EmailStr | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;':\"<>,.?/" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v

    def to_input(self) -> SignupInput:
        return SignupInput(
            username=self.username,
            password=self.password,
            email=str(self.email) if self.email else None,
        )


class LoginRequest(BaseModel):
    username: str
    password: str

    def to_input(self) -> LoginInput:
        return LoginInput(username=self.username, password=self.password)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr | None = None
    created_at: datetime


class MeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    roles: list[str]
    permissions: list[str]
    is_super_user: bool


def make_refresh_input(refresh_token: str) -> RefreshInput:
    return RefreshInput(refresh_token=refresh_token)


def make_logout_input(refresh_token: str, payload: dict[str, object]) -> LogoutInput:
    return LogoutInput(
        refresh_token=refresh_token,
        jti=str(payload["jti"]),
        exp=int(payload["exp"]),  # type: ignore[arg-type]
    )
