from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request


async def test_ip_rate_limit_exceeded():
    from app.core.rate_limit import IP_MAX_ATTEMPTS, rate_limit_by_ip

    # Mock redis_client.incr to return IP_MAX_ATTEMPTS + 1
    mock_incr = AsyncMock(return_value=IP_MAX_ATTEMPTS + 1)
    mock_expire = AsyncMock()

    # Create a mock Request with client.host
    mock_client = AsyncMock()
    mock_client.host = "192.168.1.1"
    mock_request = AsyncMock(spec=Request)
    mock_request.client = mock_client
    mock_request.url.path = "/test"

    # Patch the redis_client to use our mocks
    with patch("app.core.rate_limit.redis_client") as mock_redis:
        mock_redis.incr = mock_incr
        mock_redis.expire = mock_expire

        # Call rate_limit_by_ip and expect HTTPException 429 to be raised
        with pytest.raises(HTTPException) as exc_info:
            await rate_limit_by_ip(mock_request)

        # Assert HTTPException 429 is raised
        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded (IP)" in exc_info.value.detail

        # Verify that incr was called once
        mock_incr.assert_called_once()


async def test_ip_rate_limit_with_no_client():
    from app.core.rate_limit import IP_MAX_ATTEMPTS, rate_limit_by_ip

    # Mock redis_client.incr to return less than the limit
    mock_incr = AsyncMock(return_value=IP_MAX_ATTEMPTS - 5)  # Below the limit
    mock_expire = AsyncMock()

    # Create a mock Request with no client (will default to "unknown")
    mock_request = AsyncMock(spec=Request)
    mock_request.client = None
    mock_request.url.path = "/test"

    # Patch the redis_client to use our mocks
    with patch("app.core.rate_limit.redis_client") as mock_redis:
        mock_redis.incr = mock_incr
        mock_redis.expire = mock_expire

        # Call rate_limit_by_ip - should not raise an exception
        await rate_limit_by_ip(mock_request)

        # Verify that incr was called once (with "unknown" IP)
        mock_incr.assert_called_once()


async def test_username_rate_limit_exceeded():
    from app.core.rate_limit import USERNAME_MAX_ATTEMPTS, rate_limit_by_username

    # Mock redis_client.incr to return USERNAME_MAX_ATTEMPTS + 1
    mock_incr = AsyncMock(return_value=USERNAME_MAX_ATTEMPTS + 1)
    mock_expire = AsyncMock()

    # Create a mock Request with JSON body containing username
    mock_request = AsyncMock(spec=Request)
    mock_request.body = AsyncMock(return_value=b'{"username": "testuser"}')
    mock_request.url.path = "/login"

    # Patch the redis_client to use our mocks
    with patch("app.core.rate_limit.redis_client") as mock_redis:
        mock_redis.incr = mock_incr
        mock_redis.expire = mock_expire

        # Call rate_limit_by_username and expect HTTPException 429 to be raised
        with pytest.raises(HTTPException) as exc_info:
            await rate_limit_by_username(mock_request)

        # Assert HTTPException 429 is raised
        assert exc_info.value.status_code == 429
        assert "Rate limit exceeded (USERNAME)" in exc_info.value.detail

        # Verify that incr was called once
        mock_incr.assert_called_once()


async def test_username_rate_limit_not_exceeded():
    from app.core.rate_limit import USERNAME_MAX_ATTEMPTS, rate_limit_by_username

    # Mock redis_client.incr to return less than the limit
    mock_incr = AsyncMock(return_value=USERNAME_MAX_ATTEMPTS - 5)  # Below the limit
    mock_expire = AsyncMock()

    # Create a mock Request with JSON body containing username
    mock_request = AsyncMock(spec=Request)
    mock_request.body = AsyncMock(return_value=b'{"username": "testuser"}')
    mock_request.url.path = "/login"

    # Patch the redis_client to use our mocks
    with patch("app.core.rate_limit.redis_client") as mock_redis:
        mock_redis.incr = mock_incr
        mock_redis.expire = mock_expire

        # Call rate_limit_by_username - should not raise an exception
        await rate_limit_by_username(mock_request)

        # Verify that incr was called once
        mock_incr.assert_called_once()


async def test_ip_rate_limit_with_empty_host():
    from app.core.rate_limit import rate_limit_by_ip

    # Create a mock Request with empty host
    mock_client = AsyncMock()
    mock_client.host = ""  # Empty host
    mock_request = AsyncMock(spec=Request)
    mock_request.client = mock_client
    mock_request.url.path = "/test"

    # Patch the redis_client to ensure it's not called
    with patch("app.core.rate_limit.redis_client") as mock_redis:
        # Call rate_limit_by_ip - should not raise an exception and not call redis
        await rate_limit_by_ip(mock_request)

        # Verify that neither incr nor expire was called since IP is empty
        mock_redis.incr.assert_not_called()
        mock_redis.expire.assert_not_called()


async def test_ip_rate_limit_not_exceeded():
    from app.core.rate_limit import IP_MAX_ATTEMPTS, rate_limit_by_ip

    # Mock redis_client.incr to return less than the limit
    mock_incr = AsyncMock(return_value=IP_MAX_ATTEMPTS - 5)  # Below the limit
    mock_expire = AsyncMock()

    # Create a mock Request with client.host
    mock_client = AsyncMock()
    mock_client.host = "192.168.1.1"
    mock_request = AsyncMock(spec=Request)
    mock_request.client = mock_client
    mock_request.url.path = "/test"

    # Patch the redis_client to use our mocks
    with patch("app.core.rate_limit.redis_client") as mock_redis:
        mock_redis.incr = mock_incr
        mock_redis.expire = mock_expire

        # Call rate_limit_by_ip - should not raise an exception
        await rate_limit_by_ip(mock_request)

        # Verify that incr was called once
        mock_incr.assert_called_once()
