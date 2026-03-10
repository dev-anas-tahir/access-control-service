"""Security core logic for the application."""

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext

from app.config import settings
from app.core.keys import key_pair

pwd_context = CryptContext(
    schemes=["bcrypt", "django_pbkdf2_sha256"], deprecated="auto"
)


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a hashed one."""
    return pwd_context.verify(password, hashed)


def needs_rehash(hashed: str) -> bool:
    """Returns True if the hash needs upgrading — used for Django migration."""
    return pwd_context.needs_update(hashed)


def create_access_token(
    user_id: str,
    username: str,
    roles: list[str],
    permissions: list[str],
    is_super_admin: bool,
) -> str:
    """Create an access token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": expire,
        "jti": str(uuid.uuid4()),
        "username": username,
        "roles": roles,
        "permissions": permissions,
        "is_super_admin": is_super_admin,
    }
    return jwt.encode(payload, key_pair.private_key, algorithm=settings.jwt_algorithm)


def verify_access_token(
    token: str,
) -> dict:
    """Verify an access token and return the payload."""
    try:
        payload = jwt.decode(
            token,
            key_pair.public_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "jti", "iss"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}")
