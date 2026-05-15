import uuid

from sqlalchemy import (
    UUID,
    Boolean,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.catalog.domain.entities.product import ProductStatus
from app.catalog.infrastructure.orm.category import Category
from app.shared.infrastructure.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[ProductStatus] = mapped_column(
        Enum(ProductStatus, name="product_status"),
        nullable=False,
        default=ProductStatus.INACTIVE,
        server_default=ProductStatus.INACTIVE.value,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    category: Mapped[Category] = relationship("Category", back_populates="products")
    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant", back_populates="product", cascade="all, delete-orphan"
    )


class ProductVariant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "product_variants"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    sku: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    product: Mapped[Product] = relationship("Product", back_populates="variants")

    __table_args__ = (UniqueConstraint("sku", name="uq_product_variants_sku"),)
