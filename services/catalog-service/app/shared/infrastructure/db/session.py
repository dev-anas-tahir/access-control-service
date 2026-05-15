from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

async_engine: AsyncEngine = create_async_engine(
    str(settings.database_url),
    echo=settings.app_debug,
    pool_size=settings.pool_size,
    max_overflow=settings.max_overflow,
)

async_session_factory: async_sessionmaker = async_sessionmaker(
    async_engine,
    expire_on_commit=False,
)
