import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from shared.logging import setup_logging
from shared.middleware import RequestResponseMiddleware
from sqlalchemy import text

from app.catalog.infrastructure.http import routes as catalog_routes
from app.catalog.infrastructure.http.exception_mapper import (
    register_catalog_exception_handlers,
)
from app.config import settings
from app.inventory.infrastructure.http import routes as inventory_routes
from app.inventory.infrastructure.http.exception_mapper import (
    register_inventory_exception_handlers,
)
from app.shared.infrastructure.db.session import async_engine
from app.shared.infrastructure.http.jwks import jwks_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.app_debug:
        setup_logging(settings.log_level)

    logger.info("Starting up catalog-service...")

    try:
        await jwks_client.load()
        logger.info("JWKS loaded from %s", settings.iam_jwks_url)
    except Exception as e:
        raise RuntimeError(f"Failed to load JWKS: {e}")

    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection established")
    except Exception as e:
        raise RuntimeError(f"Database connection failed: {e}")

    yield

    logger.info("Shutting down catalog-service...")
    await async_engine.dispose()
    logger.info("Database connections closed")


app = FastAPI(
    title="Catalog Service",
    version="1.0.0",
    description="Product catalog and inventory management",
    docs_url="/docs" if settings.app_env.lower() != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(RequestResponseMiddleware)

register_catalog_exception_handlers(app)
register_inventory_exception_handlers(app)

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(catalog_routes.router)
api_v1.include_router(inventory_routes.router)
app.include_router(api_v1)
