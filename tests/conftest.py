import types
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import settings
from app.main import app
from app.shared.infrastructure.db.base import Base
from app.shared.infrastructure.db.session import get_db


# ──────────── Test Engine ──────────── #
@pytest_asyncio.fixture(scope="session")
async def engine():
    # 1. Look if test_database_url is configured
    if not settings.test_database_url:
        pytest.skip("TEST_DATABASE_URL not configured")

    # 2. Create async engine pointing at TEST database
    async_engine: AsyncEngine = create_async_engine(
        str(settings.test_database_url),
        echo=False,
        poolclass=NullPool,
    )

    # 3. Create all tables on test DB
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # 4. Yield the engine — sessions created in db fixture
    yield async_engine

    # 5. Drop everything after session
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    # 6. Dispose engine
    await async_engine.dispose()


# ──────────── DB Session ──────────── #
@pytest_asyncio.fixture
async def db(engine):
    """Fresh session per test — data truncated after each test."""
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    # Yield session to test
    async with session_factory() as session:
        yield session

    # Truncate in a separate clean session after test completes
    async with session_factory() as cleanup_session:
        await cleanup_session.execute(
            text(
                "TRUNCATE users, roles, permissions, "
                "user_roles, role_permissions, audit_logs "
                "RESTART IDENTITY CASCADE"
            )
        )
        await cleanup_session.commit()


# ──────────── Override get_db dependency ──────────── #
@pytest.fixture
def override_get_db(db):
    # 1. Override FastAPI's get_db dependency
    async def _get_db():
        yield db

    app.dependency_overrides[get_db] = _get_db
    # 2. To use test session instead
    yield

    # Clean up the override after the test
    app.dependency_overrides.clear()


# ──────────── Mock Redis ──────────── #
@pytest_asyncio.fixture(scope="session")
async def mock_redis():
    """Mock Redis client to avoid actual Redis connections during tests."""
    from app.auth.infrastructure import composition as auth_composition_module
    from app.shared.infrastructure.cache import redis as redis_module
    from app.shared.infrastructure.http import rate_limit as rate_limit_module

    # Create a mock Redis client
    mock_client = AsyncMock()
    mock_client.ping = AsyncMock(return_value=True)
    mock_client.get = AsyncMock(return_value=None)
    mock_client.setex = AsyncMock(return_value=True)
    mock_client.incr = AsyncMock(return_value=1)
    mock_client.expire = AsyncMock(return_value=True)
    mock_client.delete = AsyncMock(return_value=1)
    mock_client.lpush = AsyncMock(return_value=1)
    mock_client.lrange = AsyncMock(return_value=[])
    mock_client.zadd = AsyncMock(return_value=1)
    mock_client.zrange = AsyncMock(return_value=[])
    mock_client.zrem = AsyncMock(return_value=1)

    # Patch the redis_client in all modules that import it
    patches = [
        patch.object(redis_module, "redis_client", mock_client),
        patch.object(rate_limit_module, "redis_client", mock_client),
        patch.object(auth_composition_module, "redis_client", mock_client),
    ]

    # Start all patches
    for p in patches:
        p.start()

    yield mock_client

    # Stop all patches
    for p in patches:
        p.stop()


# ──────────── Mock JWT and RSA Keys ──────────── #
@pytest_asyncio.fixture(scope="session")
def mock_jwt():
    """Inject test RSA keys into the key_pair singleton used by composition adapters.

    Mutates key_pair._private_key / ._public_key in place so that
    JwtTokenIssuer and JwtTokenVerifier (which hold a reference to the same
    singleton) sign and verify with real crypto but with test-only keys.
    """
    from cryptography.hazmat.primitives.asymmetric import rsa

    from app.auth.infrastructure.crypto import key_pair as keys_module

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    original_private = keys_module.key_pair._private_key
    original_public = keys_module.key_pair._public_key

    # Inject test keys into the singleton; composition adapters share this object
    keys_module.key_pair._private_key = private_key
    keys_module.key_pair._public_key = public_key

    # Prevent lifespan from overwriting the test keys when it calls key_pair.load()
    keys_module.key_pair.load = lambda *_args, **_kwargs: None

    yield types.SimpleNamespace(private_key=private_key, public_key=public_key)

    # Restore original state
    keys_module.key_pair._private_key = original_private
    keys_module.key_pair._public_key = original_public
    del keys_module.key_pair.load  # remove instance attribute; restores class method
