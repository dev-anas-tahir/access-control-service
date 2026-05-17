from fastapi import FastAPI

from app.catalog.domain.exceptions import (
    CategoryNotFoundError,
    CategorySlugAlreadyExistsError,
    ProductNotFoundError,
    ProductVariantNotFoundError,
    SkuAlreadyExistsError,
)
from app.shared.infrastructure.http.exception_utils import register_exception_handlers


def register_catalog_exception_handlers(app: FastAPI) -> None:
    register_exception_handlers(
        app,
        {
            ProductNotFoundError: 404,
            ProductVariantNotFoundError: 404,
            SkuAlreadyExistsError: 409,
            CategoryNotFoundError: 404,
            CategorySlugAlreadyExistsError: 409,
        },
    )
