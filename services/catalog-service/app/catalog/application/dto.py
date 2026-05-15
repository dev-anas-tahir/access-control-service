import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.catalog.domain.entities.product import ProductStatus


@dataclass
class CreateProductInput:
    name: str
    description: str | None
    category_id: uuid.UUID
    actor_id: uuid.UUID


@dataclass
class ProductVariantResult:
    id: uuid.UUID
    sku: str
    price: float
    attributes: dict
    is_active: bool


@dataclass
class ProductResult:
    id: uuid.UUID
    name: str
    description: str | None
    category_id: uuid.UUID
    status: ProductStatus
    created_by: uuid.UUID
    variants: list[ProductVariantResult] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class UpdateProductInput:
    product_id: uuid.UUID
    name: str | None
    description: str | None
    category_id: uuid.UUID | None
    actor_id: uuid.UUID


@dataclass
class SetProductStatusInput:
    product_id: uuid.UUID
    active: bool
    actor_id: uuid.UUID


@dataclass
class CreateVariantInput:
    product_id: uuid.UUID
    sku: str
    price: float
    attributes: dict
    actor_id: uuid.UUID


@dataclass
class UpdateVariantInput:
    variant_id: uuid.UUID
    price: float | None
    attributes: dict | None
    is_active: bool | None
    actor_id: uuid.UUID


@dataclass
class CreateCategoryInput:
    name: str
    slug: str
    parent_id: uuid.UUID | None
    actor_id: uuid.UUID


@dataclass
class CategoryResult:
    id: uuid.UUID
    name: str
    slug: str
    parent_id: uuid.UUID | None
    created_at: datetime | None = None
