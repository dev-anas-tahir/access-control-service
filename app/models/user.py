import uuid

from sqlalchemy import UUID, Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin


class User(TimestampMixin, SoftDeleteMixin, Base):
    """
    User model representing a user in the system.

    This model includes fields for user information and authentication, with
    relationships to roles and permissions.

    Attributes:
        id: Unique identifier for the user (UUID).
        username: Unique username for the user (max 255 characters).
        email: Email address for the user (max 255 characters, optional).
        password_hash: Hashed password for authentication.
        is_super_user: Flag indicating if the user has super user privileges.
        is_active: Flag indicating if the user account is active.
        organization_id: Reference to the user's organization (optional).
        roles: Relationship to Role objects through the user_roles association table.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_super_user: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, server_default=text("true"), nullable=False
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    roles: Mapped[list["Role"]] = relationship(  # type: ignore  # noqa: F821
        "Role",
        secondary="user_roles",
        primaryjoin="User.id == UserRole.user_id",
        secondaryjoin="UserRole.role_id == Role.id",
        back_populates="users",
    )
