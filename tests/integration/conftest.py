"""
Integration test configuration.

This conftest enables the real lifespan for integration tests while ensuring
the database engine and other dependencies are properly configured for the test environment.
"""  # noqa: E501

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import settings
from app.db.session import async_engine as prod_async_engine
from app.db.session import get_db
from app.main import app
from app.models.base import Base
from app.models.role import Role
from app.models.user import User
from app.services.auth_service import hash_password


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


# ──────────── Admin user fixture ──────────── #
@pytest_asyncio.fixture
async def admin_user(db):
    """Create a user with super_user privileges for admin endpoints."""
    admin = User(
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("AdminPass123!"),
        is_super_user=True,
        is_active=True,
    )
    db.add(admin)
    await db.flush()
    await db.refresh(admin)
    return admin


# ──────────── Admin token fixture ──────────── #
@pytest_asyncio.fixture
async def admin_token(admin_user, mock_jwt):
    """Generate a real JWT access token for the admin user using test keys."""
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    import jwt

    from app.config import settings

    # Build payload with proper timestamps
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload = {
        "sub": str(admin_user.id),
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": expire,
        "jti": str(uuid4()),
        "username": admin_user.username,
        "roles": ["admin"],
        "permissions": ["*"],
        "is_super_user": True,
    }

    # Use the mock_jwt's private key to sign the token (real JWT encoding)
    token = jwt.encode(payload, mock_jwt.private_key, algorithm=settings.jwt_algorithm)

    return token


# ──────────── Regular user fixture ──────────── #
@pytest_asyncio.fixture
async def regular_user(db):
    """Create a regular user for role assignment tests."""
    user = User(
        username="regularuser",
        email="user@example.com",
        password_hash=hash_password("UserPass123!"),
        is_super_user=False,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


# ──────────── Viewer role fixture ──────────── #
@pytest_asyncio.fixture
async def viewer_role(db):
    """Ensure required roles exist in the database for testing."""
    # Check if viewer role exists
    result = await db.execute(select(Role).where(Role.name == "viewer"))
    role = result.scalar_one_or_none()

    if not role:
        role = Role(name="viewer", description="Default viewer role", is_system=True)
        db.add(role)
        await db.flush()
    return role


# ──────────── Mock Redis ──────────── #
@pytest_asyncio.fixture(scope="session")
async def mock_redis():
    """Mock Redis client to avoid actual Redis connections during tests."""
    from app.core import dependencies as dependencies_module
    from app.core import rate_limit as rate_limit_module
    from app.db import redis as redis_module
    from app.services import auth_service as auth_service_module

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
        patch.object(auth_service_module, "redis_client", mock_client),
        patch.object(dependencies_module, "redis_client", mock_client),
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
    """Mock RSA keys only — JWT encode/decode use real crypto in integration tests."""

    from cryptography.hazmat.primitives.asymmetric import rsa

    from app.core import keys as keys_module
    from app.core import security as security_module

    # Create a real RSA key pair for testing purposes
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    # Create a mock key pair that behaves like the real one
    mock_key_pair = MagicMock()
    mock_key_pair.private_key = private_key
    mock_key_pair.public_key = public_key

    # Patch key_pair in both security and keys modules (where it's used)
    # Do NOT patch jwt.encode or jwt.decode — let them work with real crypto
    patches = [
        patch.object(security_module, "key_pair", mock_key_pair),
        patch.object(keys_module, "key_pair", mock_key_pair),
        # Also patch the class instantiation to return our mock
        patch.object(keys_module, "RSAKeyPair", return_value=mock_key_pair),
    ]

    for p in patches:
        p.start()

    # Expose the mock key pair for test fixtures to use for token generation
    yield mock_key_pair

    for p in patches:
        p.stop()


# ──────────── HTTP client ──────────── #
@pytest_asyncio.fixture
async def client(override_get_db):
    # 1. Create AsyncClient with ASGITransport(app=app)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        # 2. Base_url="http://test"
        base_url="http://test",
    ) as ac:
        yield ac


# ──────────── Override Database Engine ──────────── #
@pytest_asyncio.fixture(scope="session", autouse=True)
def override_engine(engine):
    """Override the production database engine with the test engine."""
    original_engine = prod_async_engine
    # Import here to avoid circular import issues
    import app.db.session as session_module

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
