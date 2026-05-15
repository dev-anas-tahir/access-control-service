import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.shared.infrastructure.db.base import Base

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture(scope="session")
def engine():
    if not TEST_DB_URL:
        pytest.skip("TEST_DATABASE_URL not set")
    eng = create_async_engine(TEST_DB_URL, echo=False)
    yield eng
    import asyncio

    asyncio.get_event_loop().run_until_complete(eng.dispose())


@pytest_asyncio.fixture(scope="session")
async def create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db(engine, create_tables) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
        await session.rollback()
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


@pytest_asyncio.fixture
async def client(db) -> AsyncGenerator[AsyncClient, None]:
    from unittest.mock import MagicMock

    from app.main import app
    from app.shared.infrastructure.http.jwks import jwks_client

    jwks_client._public_key = MagicMock()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
