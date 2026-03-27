"""
Unit tests for auth_service pure logic (no real DB/Redis).

Per AGENTS.md: "Test pure logic only: JWT encoding/decoding, password hashing,
permission checks, schema validation. No real DB, Redis, or HTTP calls.
Mock all external dependencies."
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.services import auth_service


async def test_logout_deletes_refresh_token():
    """Test that logout deletes the refresh token from Redis."""
    # Mock Redis client methods
    mock_delete = AsyncMock()
    mock_setex = AsyncMock()

    # Create a sample JWT payload
    jwt_payload = {
        "jti": "test-jti-12345",
        "exp": int(datetime.now(timezone.utc).timestamp()) + 3600,  # 1 hour from now
        "user_id": "test-user-id",
    }

    # Patch Redis client
    with patch("app.services.auth_service.redis_client") as mock_redis:
        mock_redis.delete = mock_delete
        mock_redis.setex = mock_setex

        # Call logout
        await auth_service.logout("test_refresh_token", jwt_payload)

        # Verify Redis delete was called for refresh token
        mock_delete.assert_any_call("refresh_token:test_refresh_token")

        # Verify Redis setex was called for JTI revocation
        mock_setex.assert_called_once()
        # Verify the JTI was stored with the correct key
        call_args = mock_setex.call_args
        assert call_args[0][0] == "revoked_jti:test-jti-12345"
        assert call_args[0][2] == "1"  # The value stored


async def test_logout_revokes_jti_with_correct_ttl():
    """Test that logout revokes the access token JTI with correct TTL."""
    mock_delete = AsyncMock()
    mock_setex = AsyncMock()

    # Create payload with known expiry
    now = int(datetime.now(timezone.utc).timestamp())
    exp = now + 3600  # Expires in 1 hour
    jwt_payload = {
        "jti": "test-jti-99999",
        "exp": exp,
        "user_id": "test-user-id",
    }

    with patch("app.services.auth_service.redis_client") as mock_redis:
        mock_redis.delete = mock_delete
        mock_redis.setex = mock_setex

        await auth_service.logout("refresh_token_xyz", jwt_payload)

        # Verify setex was called with TTL close to 3600 seconds
        call_args = mock_setex.call_args
        ttl = call_args[0][1]
        # TTL should be approximately 3600 (accounting for a few seconds of execution time)  # noqa: E501
        assert 3595 <= ttl <= 3600


async def test_logout_handles_expired_token_gracefully():
    """Test that logout handles already-expired tokens without errors."""
    mock_delete = AsyncMock()
    mock_setex = AsyncMock()

    # Create payload that's already expired
    now = int(datetime.now(timezone.utc).timestamp())
    exp = now - 3600  # Expired 1 hour ago
    jwt_payload = {
        "jti": "expired-jti",
        "exp": exp,
        "user_id": "test-user-id",
    }

    with patch("app.services.auth_service.redis_client") as mock_redis:
        mock_redis.delete = mock_delete
        mock_redis.setex = mock_setex

        # Should not raise an error
        await auth_service.logout("refresh_token_expired", jwt_payload)

        # Refresh token should still be deleted
        mock_delete.assert_called_once_with("refresh_token:refresh_token_expired")

        # JTI revocation should not be set (TTL is 0 or negative)
        # Check that setex was either not called or called with TTL=0
        if mock_setex.called:
            call_args = mock_setex.call_args
            ttl = call_args[0][1]
            assert ttl == 0  # TTL is clamped to 0 by max(exp - now, 0)
