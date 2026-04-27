"""
Integration test configuration.

This conftest enables the real lifespan for integration tests while ensuring
the database engine and other dependencies are properly configured for the test environment.
"""  # noqa: E501

import types
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
from app.shared.infrastructure.crypto.bcrypt_password_hasher import BcryptPasswordHasher

_hasher = BcryptPasswordHasher()


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
        password_hash=_hasher.hash("AdminPass123!"),
        is_super_user=True,
        is_active=True,
    )
    db.add(admin)
    await db.flush()
    await db.refresh(admin)
    await db.commit()
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
        password_hash=_hasher.hash("UserPass123!"),
        is_super_user=False,
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    await db.commit()
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
        await db.commit()
    return role


# ──────────── Mock Redis ──────────── #
@pytest_asyncio.fixture(scope="session")
async def mock_redis():
    """Mock Redis client to avoid actual Redis connections during tests."""
    from app.auth.infrastructure import composition as auth_composition_module
    from app.core import rate_limit as rate_limit_module
    from app.db import redis as redis_module

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

    Mutates app.core.keys.key_pair._private_key / ._public_key in place so that
    JwtTokenIssuer and JwtTokenVerifier (which hold a reference to the same
    singleton) sign and verify with real crypto but with test-only keys.
    """
    from cryptography.hazmat.primitives.asymmetric import rsa

    from app.core import keys as keys_module

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
    """Override the production engine AND session factory in all composition roots.

    async_session_factory is an async_sessionmaker bound at import time to the
    production engine. Simply swapping async_engine doesn't help — each
    composition module holds its own reference to the factory object. We must
    also replace that reference everywhere it was imported.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    import app.audit.infrastructure.composition as audit_comp
    import app.auth.infrastructure.composition as auth_comp
    import app.db.session as session_module
    import app.rbac.infrastructure.composition as rbac_comp

    test_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )

    original_engine = session_module.async_engine
    original_factory = session_module.async_session_factory

    session_module.async_engine = engine
    session_module.async_session_factory = test_factory
    auth_comp.async_session_factory = test_factory
    rbac_comp.async_session_factory = test_factory
    audit_comp.async_session_factory = test_factory

    yield

    session_module.async_engine = original_engine
    session_module.async_session_factory = original_factory
    auth_comp.async_session_factory = original_factory
    rbac_comp.async_session_factory = original_factory
    audit_comp.async_session_factory = original_factory


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

    # Import modules here to avoid circular import issues
    import app.api.v1.jwks as jwks_module
    import app.main as main_module

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
