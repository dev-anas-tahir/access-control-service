import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


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
        """Set status to ACTIVE. Returns True if this is a new activation (was inactive)."""
        was_inactive = self.status == ProductStatus.INACTIVE
        self.status = ProductStatus.ACTIVE
        return was_inactive

    def deactivate(self) -> None:
        self.status = ProductStatus.INACTIVE
