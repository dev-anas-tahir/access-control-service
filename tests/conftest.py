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
from app.db.session import get_db
from app.main import app
from app.models.base import Base
from app.models.role import Role


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
