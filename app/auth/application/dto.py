import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SignupInput:
    username: str
    password: str
    email: str | None = None


@dataclass
class SignupResult:
    id: uuid.UUID
    username: str
    email: str | None
    created_at: datetime | None


@dataclass
class LoginInput:
    username: str
    password: str


@dataclass
class LoginResult:
    access_token: str
    refresh_token: str


@dataclass
class RefreshInput:
    refresh_token: str


@dataclass
class RefreshResult:
    access_token: str
    refresh_token: str


@dataclass
class LogoutInput:
    refresh_token: str
    jti: str
    exp: int
