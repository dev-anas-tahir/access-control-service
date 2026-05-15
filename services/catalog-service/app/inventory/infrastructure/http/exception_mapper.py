from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.inventory.domain.exceptions import (
    InsufficientStockError,
    InventoryNotFoundError,
)


def register_inventory_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InventoryNotFoundError)
    async def _not_found(request: Request, exc: InventoryNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(InsufficientStockError)
    async def _insufficient(
        request: Request, exc: InsufficientStockError
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})
