"""
Unit tests for core dependencies (require_super_user, get_current_user).

Per AGENTS.md: "Test pure logic only. No real DB, Redis, or HTTP calls.
Mock all external dependencies."
"""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.domain.exceptions import InvalidTokenError
from app.auth.domain.ports.token_verifier import TokenPayload
from app.auth.infrastructure.http.dependencies import (
    get_current_user,
    require_super_user,
)
from tests.unit.auth.fakes import FakeRevocationStore, FakeTokenVerifier

# ──────────────────────────────────────────────────────────────
# get_current_user
# ──────────────────────────────────────────────────────────────


async def test_get_current_user_valid_token():
    """Test get_current_user with a valid token."""
    expected_payload: TokenPayload = {
        "sub": "user-123",
        "is_super_user": False,
        "jti": "jti-123",
        "exp": 9999999999,
        "iss": "test",
        "iat": 0,
        "username": "testuser",
        "roles": [],
        "permissions": [],
    }
    verifier = FakeTokenVerifier(payload=expected_payload)
    revocation_store = FakeRevocationStore()

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="valid.jwt.token"
    )
    result = await get_current_user(credentials, verifier, revocation_store)

    assert result == expected_payload


async def test_get_current_user_invalid_token():
    """Test get_current_user with an invalid token raises HTTPException."""
    verifier = FakeTokenVerifier(raises=InvalidTokenError)
    revocation_store = FakeRevocationStore()

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="bad.jwt.token"
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials, verifier, revocation_store)

    assert exc_info.value.status_code == 401
    assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"


async def test_get_current_user_revoked_token():
    """Test get_current_user with a revoked token raises HTTPException."""
    payload: TokenPayload = {
        "sub": "user-123",
        "is_super_user": False,
        "jti": "revoked-jti",
        "exp": 9999999999,
        "iss": "test",
        "iat": 0,
        "username": "testuser",
        "roles": [],
        "permissions": [],
    }
    verifier = FakeTokenVerifier(payload=payload)
    revocation_store = FakeRevocationStore()
    await revocation_store.revoke("revoked-jti", 900)

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer", credentials="revoked.jwt.token"
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials, verifier, revocation_store)

    assert exc_info.value.status_code == 401
    assert "Token has been revoked" in exc_info.value.detail
    assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"


# ──────────────────────────────────────────────────────────────
# require_super_user
# ──────────────────────────────────────────────────────────────


async def test_require_super_user_with_super_user():
    """Test require_super_user when user has super_user privileges."""
    payload: TokenPayload = {
        "sub": "admin-123",
        "is_super_user": True,
        "jti": "jti-123",
        "exp": 9999999999,
        "iss": "test",
        "iat": 0,
        "username": "admin",
        "roles": [],
        "permissions": [],
    }

    result = await require_super_user(payload)

    assert result == payload


async def test_require_super_user_without_super_user():
    """
    Test require_super_user when user lacks super_user privileges raises HTTPException.
    """
    payload: TokenPayload = {
        "sub": "user-123",
        "is_super_user": False,
        "jti": "jti-123",
        "exp": 9999999999,
    }

    with pytest.raises(HTTPException) as exc_info:
        await require_super_user(payload)

    assert exc_info.value.status_code == 403
    assert "Super user privileges required" in exc_info.value.detail


async def test_require_super_user_missing_is_super_user():
    """
    Test require_super_user when payload lacks is_super_user field raises HTTPException.
    """
    payload: TokenPayload = {
        "sub": "user-123",
        "jti": "jti-123",
        "exp": 9999999999,
    }

    with pytest.raises(HTTPException) as exc_info:
        await require_super_user(payload)

    assert exc_info.value.status_code == 403
    assert "Super user privileges required" in exc_info.value.detail
