import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.config import settings
from app.core.keys import key_pair
from app.db.redis import redis_client
from app.db.session import async_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager to handle startup and shutdown events for the
    FastAPI application
    This function will be called when the application starts and stops, allowing
    us to perform necessary initialization and cleanup tasks such as loading RSA
    keys, connecting to databases, etc.
    """

    # ──────────── START UP ──────────── #
    logger.info("Starting up...")

    # 1. load the RSA keys
    try:
        key_pair.load(settings.private_key_path, settings.public_key_path)
        logger.info("✅ RSA keys loaded")
    except FileNotFoundError as e:
        raise RuntimeError(
            f"❌ RSA key file not found: {e}. Did you run openssl keygen?"
        )

    # 2. connect to database
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection established")
    except Exception as e:
        raise RuntimeError(f"❌ Database connection failed: {e}")

    # 3. connect to redis
    try:
        await redis_client.ping()
        logger.info("✅ Redis connection established")
    except Exception as e:
        raise RuntimeError(f"❌ Redis connection failed: {e}")

    # 4. connect to pub/sub      ← next

    yield

    # ──────────── SHUTDOWN ──────────── #
    logger.info("Shutting down...")

    # 1. close database connection
    await async_engine.dispose()
    logger.info("✅ Database connections closed")

    # 2. close redis connection
    await redis_client.aclose()
    logger.info("✅ Redis connection closed")

    # 3. close pub/sub connection


app = FastAPI(lifespan=lifespan)
