import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.db.session import get_db
from app.main import app
from app.models.base import Base


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
    )

    # 3. Yield it
    yield async_engine

    # 4. Dispose after session
    await async_engine.dispose()


# ──────────── Tables ──────────── #
@pytest_asyncio.fixture(scope="session")
async def create_tables(engine):
    # 1. Create all tables on test DB
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 2. Yield the tables
    yield
    
    # 3. Drop all after session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ──────────── DB Session with rollback ──────────── #
@pytest_asyncio.fixture
async def db(engine, create_tables):
    # 1. Connect to engine
    connection = await engine.connect()

    # 2. Begin transaction
    transaction = await connection.begin()

    # 3. Create session bound to that connection
    async_session = async_sessionmaker(
        connection,
        class_=AsyncSession,
        expire_on_commit=False,
        )
    async with async_session() as session:
        # 4. Yield session
        yield session

        # 5. Rollback transaction
        await transaction.rollback()
    
    await connection.close()


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
        base_url="http://test"
    ) as ac:
        yield ac
