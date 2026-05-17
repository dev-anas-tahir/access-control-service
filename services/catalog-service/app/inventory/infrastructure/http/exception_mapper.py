from fastapi import FastAPI

from app.inventory.domain.exceptions import (
    InsufficientStockError,
    InventoryNotFoundError,
)
from app.shared.infrastructure.http.exception_utils import register_exception_handlers


def register_inventory_exception_handlers(app: FastAPI) -> None:
    register_exception_handlers(
        app,
        {
            InventoryNotFoundError: 404,
            InsufficientStockError: 409,
        },
    )
