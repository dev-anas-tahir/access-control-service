import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from app.catalog.domain.events import CatalogEvent, ProductPriceChanged


class ProductStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass
class ProductVariant:
    id: uuid.UUID
    product_id: uuid.UUID
    sku: str
    price: float
    attributes: dict = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Product:
    id: uuid.UUID
    name: str
    description: str | None
    category_id: uuid.UUID
    status: ProductStatus
    created_by: uuid.UUID
    variants: list[ProductVariant] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def activate(self) -> bool:
        was_inactive = self.status == ProductStatus.INACTIVE
        self.status = ProductStatus.ACTIVE
        return was_inactive

    def deactivate(self) -> None:
        self.status = ProductStatus.INACTIVE

    def update_variant_price(
        self,
        variant: "ProductVariant",
        new_price: float,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> CatalogEvent | None:
        if new_price == variant.price:
            return None
        old_price = variant.price
        variant.price = new_price
        if self.status == ProductStatus.ACTIVE:
            return ProductPriceChanged(
                actor_id=actor_id,
                product_id=self.id,
                variant_id=variant.id,
                sku=variant.sku,
                old_price=old_price,
                new_price=new_price,
            )
        return None
