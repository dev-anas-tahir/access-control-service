from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

"""
Create an asynchronous SQLAlchemy engine using the database URL from the settings. The
`echo=False` option disables SQL query logging, which can be set to `True`
for debugging purposes.
"""
async_engine: create_async_engine = create_async_engine(
    str(settings.database_url),
    echo=settings.app_debug,
    pool_size=settings.pool_size,
    max_overflow=settings.max_overflow,
)

"""
Create an async session factory that will be used to create sessions for database
operations. The `expire_on_commit=False` option prevents SQLAlchemy from expiring
objects after a commit, which can be useful in certain scenarios where you want
to keep using the objects after committing changes.
"""
async_session_factory: async_sessionmaker = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to provide an asynchronous database session for FastAPI
    routes. This function is designed to be used with FastAPI's dependency
    injection system, allowing you to easily access the database session in your
    route handlers.

    The function creates a new session using the async session factory and yields
    it. After the route handler is done, the session will be automatically closed,
    ensuring proper cleanup of database resources or if an exception occurs,
    it will roll back any uncommitted changes to maintain
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
