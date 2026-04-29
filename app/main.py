"""
Main FastAPI application for the access control service.

This module defines the FastAPI application with lifespan management for handling
startup and shutdown events. It manages connections to various services including
database, Redis, and Google Cloud Pub/Sub.

The application includes:
- Startup tasks: Loading RSA keys, connecting to database, Redis, and Pub/Sub
- Shutdown tasks: Closing all connections gracefully
- Health checks and monitoring

Example:
    ```bash
    uvicorn app.main:app --reload
    ```
"""

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

# from google.api_core.exceptions import NotFound
from sqlalchemy import text

from app.api.v1 import jwks
from app.audit.infrastructure.http import routes as audit_routes
from app.auth.infrastructure.crypto.key_pair import key_pair
from app.auth.infrastructure.http import routes as auth_routes
from app.auth.infrastructure.http.exception_mapper import (
    register_auth_exception_handlers,
)
from app.config import settings
from app.core.logging import setup_logging
from app.core.middleware import RequestResponseMiddleware
from app.rbac.infrastructure.http import routes as rbac_routes
from app.rbac.infrastructure.http.exception_mapper import (
    register_rbac_exception_handlers,
)

# from app.db.pubsub import pubsub_client, topic_path
from app.shared.infrastructure.cache.redis import redis_client
from app.shared.infrastructure.db.session import async_engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager to handle startup and shutdown events for the FastAPI.

    This function is called when the application starts and stops, allowing
    us to perform necessary initialization and cleanup tasks such as loading RSA
    keys, connecting to databases, and managing service connections.

    During startup, this function:
    - Loads RSA key pairs for JWT signing
    - Establishes database connection
    - Connects to Redis
    - Verifies Pub/Sub topic availability

    During shutdown, this function:
    - Closes database connections
    - Closes Redis connection
    - Closes Pub/Sub connection

    Args:
        app: The FastAPI application instance.

    Yields:
        None: Yields control back to the application during its operational period.

    Raises:
        RuntimeError: If any of the required services fail to connect during startup.
    """

    # ──────────── START UP ──────────── #

    # 1. setup logging (before any other operations to capture logs during startup)
    if not settings.app_debug:
        setup_logging(settings.log_level)

    logger.info("Starting up...")

    # 2. load the RSA keys
    try:
        key_pair.load(settings.private_key_path, settings.public_key_path)
        logger.info("RSA keys loaded")
    except FileNotFoundError as e:
        raise RuntimeError(
            f"RSA key file not found in the dir ./keys: {e}. Did you run openssl genrsa keys/[key_name] 2048?"  # noqa: E501
        )

    # 3. connect to database
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection established")
    except Exception as e:
        raise RuntimeError(f"Database connection failed: {e}")

    # 4. connect to redis
    try:
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        raise RuntimeError(f"Redis connection failed: {e}")

    # 5. connect to pub/sub
    # try:
    #     pubsub_client.get_topic(request={"topic": topic_path})
    #     logger.info("Pub/Sub topic verified")
    # except NotFound:
    #     raise RuntimeError(
    #         f"Pub/Sub topic '{topic_path}' not found. Did you create it in GCP?"
    #     )
    # except Exception as e:
    #     raise RuntimeError(f"Pub/Sub connection failed: {e}")

    yield

    # ──────────── SHUTDOWN ──────────── #
    logger.info("Shutting down...")

    # 1. close database connection
    await async_engine.dispose()
    logger.info("Database connections closed")

    # 2. close redis connection
    await redis_client.aclose()
    logger.info("Redis connection closed")

    # 3. stop the pub/sub connection
    # pubsub_client.stop()
    # logger.info("Pub/Sub connection closed")


app = FastAPI(
    title="Access Control Service",
    version="1.0.0",
    description="Authentication, authorization, and identity management",
    docs_url="/docs" if settings.app_env.lower() != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

# Add request ID middleware
app.add_middleware(RequestResponseMiddleware)

# Register domain exception → HTTP response mappings
register_auth_exception_handlers(app)
register_rbac_exception_handlers(app)

# ──────────── JWKS at root ──────────── #
app.include_router(jwks.router)

# ──────────── API v1 ──────────── #
api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(auth_routes.router)
api_v1.include_router(rbac_routes.router)
api_v1.include_router(audit_routes.router)
app.include_router(api_v1)

# ──────────── API v2 (future) ──────────── #
api_v2 = APIRouter(prefix="/api/v2")
# TODO: Develop multiple versions of APIs in Fast API
