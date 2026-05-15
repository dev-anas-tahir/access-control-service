import uuid

from sqlalchemy import UUID, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.infrastructure.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Inventory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "inventory"

    variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    quantity_on_hand: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    quantity_reserved: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
