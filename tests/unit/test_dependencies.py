"""
Unit tests for core dependencies (require_super_user, get_current_user).

Per AGENTS.md: "Test pure logic only. No real DB, Redis, or HTTP calls.
Mock all external dependencies."
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.dependencies import get_current_user, require_super_user
from app.core.types import TokenPayload


class MockResult:
    """Helper to mock SQLAlchemy result objects."""

    def __init__(self, scalar_value=None):
        self._scalar_value = scalar_value

    def scalar_one_or_none(self):
        return self._scalar_value


# ──────────────────────────────────────────────────────────────
# get_current_user
# ──────────────────────────────────────────────────────────────


async def test_get_current_user_valid_token():
    """Test get_current_user with a valid token."""
    token = "valid.jwt.token"
    expected_payload: TokenPayload = {
        "sub": "user-123",
        "is_super_user": False,
        "jti": "jti-123",
        "exp": 9999999999,
    }

    with patch("app.core.dependencies.verify_access_token") as mock_verify:
        mock_verify.return_value = expected_payload

        # Mock Redis client
        with patch("app.core.dependencies.redis_client") as mock_redis:
            mock_redis.get = AsyncMock(return_value=None)  # Token not revoked

            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials=token
            )
            result = await get_current_user(credentials)

            assert result == expected_payload
            mock_verify.assert_called_once_with(token)
            mock_redis.get.assert_called_once_with("revoked_jti:jti-123")


async def test_get_current_user_invalid_token():
    """Test get_current_user with an invalid token raises HTTPException."""
    token = "invalid.jwt.token"

    with patch("app.core.dependencies.verify_access_token") as mock_verify:
        mock_verify.side_effect = ValueError("Invalid token")

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail
        assert exc_info.value.headers["WWW-Authenticate"] == "Bearer"


async def test_get_current_user_revoked_token():
    """Test get_current_user with a revoked token raises HTTPException."""
    token = "revoked.jwt.token"
    payload: TokenPayload = {
        "sub": "user-123",
        "is_super_user": False,
        "jti": "revoked-jti",
        "exp": 9999999999,
    }

    with patch("app.core.dependencies.verify_access_token") as mock_verify:
        mock_verify.return_value = payload

        with patch("app.core.dependencies.redis_client") as mock_redis:
            mock_redis.get = AsyncMock(return_value=True)  # Token is revoked

            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials=token
            )

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials)

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
    }

    with patch("app.core.dependencies.get_current_user") as mock_get_current:
        mock_get_current.return_value = payload

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
