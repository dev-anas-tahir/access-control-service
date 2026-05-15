import uuid

from sqlalchemy import UUID, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.infrastructure.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Category(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )
    children: Mapped[list["Category"]] = relationship(
        "Category", back_populates="parent"
    )
    parent: Mapped["Category | None"] = relationship(
        "Category", back_populates="children", remote_side="Category.id"
    )
    products: Mapped[list["Product"]] = relationship(  # noqa: F821
        "Product", back_populates="category"
    )

    __table_args__ = (UniqueConstraint("slug", name="uq_categories_slug"),)
