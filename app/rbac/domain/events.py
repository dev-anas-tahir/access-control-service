"""Domain events for the RBAC bounded context.

These events are raised by RBAC use cases and dispatched by the Unit of Work.
Handlers (typically in the audit context) subscribe to these events to create
audit log entries without direct coupling between RBAC and Audit contexts.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from app.shared.domain.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class RoleCreated(DomainEvent):
    """Event raised when a new role is created.

    Attributes:
        role_id: UUID of the created role
        name: Name of the role
        description: Optional description
        is_system: Whether this is a system role
    """

    role_id: uuid.UUID
    name: str
    description: str | None = None
    is_system: bool = False

    def to_audit_payload(self) -> dict[str, Any]:
        """Convert to payload format for audit logging."""
        return {
            "name": self.name,
            "description": self.description,
            "is_system": self.is_system,
        }


@dataclass(frozen=True, kw_only=True)
class RoleDeleted(DomainEvent):
    """Event raised when a role is soft-deleted.

    Attributes:
        role_id: UUID of the deleted role
        name: Name of the role that was deleted
    """

    role_id: uuid.UUID
    name: str

    def to_audit_payload(self) -> dict[str, Any]:
        """Convert to payload format for audit logging."""
        return {"name": self.name}


@dataclass(frozen=True, kw_only=True)
class PermissionGranted(DomainEvent):
    """Event raised when a permission is granted to a role.

    Attributes:
        role_id: UUID of the role receiving the permission
        role_name: Name of the role (denormalized for audit)
        permission_id: UUID of the permission being granted
        scope_key: The scope key (resource:action) of the permission
    """

    role_id: uuid.UUID
    role_name: str
    permission_id: uuid.UUID
    scope_key: str

    def to_audit_payload(self) -> dict[str, Any]:
        """Convert to payload format for audit logging."""
        return {
            "scope_key": self.scope_key,
            "role_name": self.role_name,
        }


@dataclass(frozen=True, kw_only=True)
class PermissionRevoked(DomainEvent):
    """Event raised when a permission is revoked from a role.

    Attributes:
        role_id: UUID of the role losing the permission
        role_name: Name of the role (denormalized for audit)
        permission_id: UUID of the permission being revoked
        scope_key: The scope key (resource:action) of the permission
    """

    role_id: uuid.UUID
    role_name: str
    permission_id: uuid.UUID
    scope_key: str

    def to_audit_payload(self) -> dict[str, Any]:
        """Convert to payload format for audit logging."""
        return {
            "scope_key": self.scope_key,
            "role_name": self.role_name,
        }


@dataclass(frozen=True, kw_only=True)
class UserRoleAssigned(DomainEvent):
    """Event raised when a role is assigned to a user.

    Attributes:
        user_id: UUID of the user receiving the role
        user_name: Username of the user (denormalized for audit)
        role_id: UUID of the role being assigned
        role_name: Name of the role (denormalized for audit)
    """

    user_id: uuid.UUID
    user_name: str
    role_id: uuid.UUID
    role_name: str

    def to_audit_payload(self) -> dict[str, Any]:
        """Convert to payload format for audit logging."""
        return {
            "user": self.user_name,
            "role": self.role_name,
        }


@dataclass(frozen=True, kw_only=True)
class UserRoleRevoked(DomainEvent):
    """Event raised when a role is revoked from a user.

    Attributes:
        user_id: UUID of the user losing the role
        user_name: Username of the user (denormalized for audit)
        role_id: UUID of the role being revoked
        role_name: Name of the role (denormalized for audit)
    """

    user_id: uuid.UUID
    user_name: str
    role_id: uuid.UUID
    role_name: str

    def to_audit_payload(self) -> dict[str, Any]:
        """Convert to payload format for audit logging."""
        return {
            "user": self.user_name,
            "role": self.role_name,
        }
