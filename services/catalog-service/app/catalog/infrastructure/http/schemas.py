import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.catalog.domain.entities.product import ProductStatus


class ProductVariantResponse(BaseModel):
    id: uuid.UUID
    sku: str
    price: float
    attributes: dict
    is_active: bool


class ProductResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    category_id: uuid.UUID
    status: ProductStatus
    created_by: uuid.UUID
    variants: list[ProductVariantResponse]
    created_at: datetime | None
    updated_at: datetime | None


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    description: str | None = None
    category_id: uuid.UUID


class ProductUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    category_id: uuid.UUID | None = None


class ProductStatusUpdate(BaseModel):
    active: bool


class VariantCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=200)
    price: float = Field(gt=0)
    attributes: dict = Field(default_factory=dict)


class VariantUpdate(BaseModel):
    price: float | None = Field(None, gt=0)
    attributes: dict | None = None
    is_active: bool | None = None


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(min_length=1, max_length=200, pattern=r"^[a-z0-9-]+$")
    parent_id: uuid.UUID | None = None


class CategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    parent_id: uuid.UUID | None
    created_at: datetime | None
