import uuid
from typing import Protocol

from app.catalog.domain.entities.product import Product, ProductVariant


class ProductRepository(Protocol):
    async def find_by_id(self, id: uuid.UUID) -> Product | None: ...

    async def list_active(self, limit: int, offset: int) -> list[Product]: ...

    async def add(
        self,
        *,
        name: str,
        description: str | None,
        category_id: uuid.UUID,
        created_by: uuid.UUID,
    ) -> Product: ...

    async def save(self, product: Product) -> None: ...

    async def add_variant(
        self,
        *,
        product_id: uuid.UUID,
        sku: str,
        price: float,
        attributes: dict,
    ) -> ProductVariant: ...

    async def sku_exists(self, sku: str) -> bool: ...

    async def find_variant_by_id(
        self, variant_id: uuid.UUID
    ) -> ProductVariant | None: ...

    async def save_variant(self, variant: ProductVariant) -> None: ...

    async def delete_variant(self, variant_id: uuid.UUID) -> None: ...
