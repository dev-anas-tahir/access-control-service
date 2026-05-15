import uuid
from datetime import datetime

from sqlalchemy import UUID, Boolean, DateTime, FetchedValue, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UUIDPrimaryKeyMixin:
    """Mixin that adds a server-generated UUID primary key column."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


class TimestampMixin:
    """Mixin to add created_at and updated_at timestamp fields to models."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=FetchedValue(),
    )


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
