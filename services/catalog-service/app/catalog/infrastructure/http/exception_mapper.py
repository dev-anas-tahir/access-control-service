from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.catalog.domain.exceptions import (
    CategoryNotFoundError,
    CategorySlugAlreadyExistsError,
    ProductNotFoundError,
    ProductVariantNotFoundError,
    SkuAlreadyExistsError,
)


def register_catalog_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProductNotFoundError)
    async def _product_not_found(
        request: Request, exc: ProductNotFoundError
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ProductVariantNotFoundError)
    async def _variant_not_found(
        request: Request, exc: ProductVariantNotFoundError
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(SkuAlreadyExistsError)
    async def _sku_exists(request: Request, exc: SkuAlreadyExistsError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(CategoryNotFoundError)
    async def _category_not_found(
        request: Request, exc: CategoryNotFoundError
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(CategorySlugAlreadyExistsError)
    async def _slug_exists(
        request: Request, exc: CategorySlugAlreadyExistsError
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
