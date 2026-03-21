"""
Integration test configuration.

This conftest enables the real lifespan for integration tests while ensuring
the database engine and other dependencies are properly configured for the test environment.
"""  # noqa: E501

from unittest.mock import MagicMock, patch

import pytest_asyncio

import app.api.v1.jwks as jwks_module
import app.main as main_module
from app.db import session as session_module


# ──────────── Override Database Engine ──────────── #
@pytest_asyncio.fixture(scope="session", autouse=True)
def override_engine(engine):
    """Override the production database engine with the test engine."""
    original_engine = session_module.async_engine
    session_module.async_engine = engine
    yield
    session_module.async_engine = original_engine


# ──────────── Patch app.main and jwks module references ──────────── #
@pytest_asyncio.fixture(scope="session", autouse=True)
def patch_app_main(mock_redis, mock_jwt, engine):
    """Patch key_pair, redis_client, and async_engine in app.main and jwks to use test doubles.

    This allows the real lifespan to run with mocked external services.
    """  # noqa: E501
    # Use the mock_key_pair from the mock_jwt fixture (already has real RSA keys)
    mock_key_pair = mock_jwt

    # Ensure the key_pair has a no-op load method
    if not hasattr(mock_key_pair, "load"):
        mock_key_pair.load = MagicMock(return_value=None)

    # mock_redis is the mock client from the root conftest
    mock_client = mock_redis

    # Apply patches to app.main module and jwks module
    patches = [
        patch.object(main_module, "key_pair", mock_key_pair),
        patch.object(main_module, "redis_client", mock_client),
        patch.object(main_module, "async_engine", engine),
        patch.object(jwks_module, "key_pair", mock_key_pair),
    ]
    for p in patches:
        p.start()

    yield

    for p in patches:
        p.stop()
