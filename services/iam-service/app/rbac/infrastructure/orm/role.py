import uuid
from datetime import datetime

from sqlalchemy import UUID, Boolean, DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.infrastructure.db.base import (
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)


class Role(UUIDPrimaryKeyMixin, SoftDeleteMixin, TimestampMixin, Base):
    """
    Role model representing a role in the system.

    This model includes fields for role information and relationships to users
    and permissions.

    Attributes:
        id: Unique identifier for the role (UUID).
        name: Unique name for the role (max 100 characters).
        description: Description of the role (optional).
        is_system: Flag indicating if the role is a system role.
        created_by: Reference to the user who created this role (optional).
        users: Relationship to User objects through the user_roles association table.
        permissions: Relationship to Permission objects through the role_permissions
                    association table.
    """

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    users: Mapped[list["User"]] = relationship(  # noqa: F821 # type: ignore
        "User",
        secondary="user_roles",
        primaryjoin="Role.id == UserRole.role_id",
        secondaryjoin="UserRole.user_id == User.id",
        back_populates="roles",
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary="role_permissions", back_populates="roles"
    )


class Permission(UUIDPrimaryKeyMixin, Base):
    """
    Permission model representing a permission in the system.

    This model includes fields for permission information and relationships to roles.

    Attributes:
        id: Unique identifier for the permission (UUID).
        resource: Resource this permission applies to (max 100 characters).
        action: Action that can be performed on the resource (max 100 characters).
        scope_key: Unique key combining resource and action for permission identification
            (max 255 characters).
        created_at: Timestamp when the permission was created.
    """  # noqa: E501

    __tablename__ = "permissions"

    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    scope_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    roles: Mapped[list["Role"]] = relationship(  # type: ignore
        "Role", secondary="role_permissions", back_populates="permissions"
    )
