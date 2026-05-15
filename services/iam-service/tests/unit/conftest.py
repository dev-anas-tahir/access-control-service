"""
Unit test configuration.

This conftest applies the lifespan override to skip real service connections
during unit tests, since unit tests focus on pure logic without infrastructure.
"""

from contextlib import asynccontextmanager

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


# ──────────── Override Lifespan for Unit Tests ──────────── #
@pytest_asyncio.fixture(scope="session", autouse=True)
async def override_lifespan_unit():
    """Override the app's lifespan to skip external service connections during unit tests."""  # noqa: E501

    # Store original lifespan
    original_lifespan = app.router.lifespan_context

    # Create a no-op lifespan that just yields
    @asynccontextmanager
    async def mock_lifespan(app):
        yield

    # Apply the override
    app.router.lifespan_context = mock_lifespan

    yield

    # Restore original lifespan after all tests
    app.router.lifespan_context = original_lifespan


# ──────────── HTTP client ──────────── #
@pytest_asyncio.fixture
async def client(override_get_db):
    """Async HTTP client for unit tests (uses mocked dependencies)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
