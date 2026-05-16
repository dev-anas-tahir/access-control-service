"""Domain events for the RBAC bounded context.

These events are raised by RBAC use cases and dispatched by the Unit of Work.
Handlers (typically in the audit context) subscribe to these events to create
audit log entries without direct coupling between RBAC and Audit contexts.
"""

import uuid
from dataclasses import dataclass

from app.shared.domain.events import AuditContext, DomainEvent


@dataclass(frozen=True, kw_only=True)
class RoleCreated(DomainEvent):
    role_id: uuid.UUID
    name: str
    description: str | None = None
    is_system: bool = False

    def to_audit_context(self) -> AuditContext:
        return AuditContext(
            action="ROLE_CREATED",
            entity_type="Role",
            entity_id=self.role_id,
            payload={
                "name": self.name,
                "description": self.description,
                "is_system": self.is_system,
            },
        )


@dataclass(frozen=True, kw_only=True)
class RoleDeleted(DomainEvent):
    role_id: uuid.UUID
    name: str

    def to_audit_context(self) -> AuditContext:
        return AuditContext(
            action="ROLE_DELETED",
            entity_type="Role",
            entity_id=self.role_id,
            payload={"name": self.name},
        )


@dataclass(frozen=True, kw_only=True)
class PermissionGranted(DomainEvent):
    role_id: uuid.UUID
    role_name: str
    permission_id: uuid.UUID
    scope_key: str

    def to_audit_context(self) -> AuditContext:
        return AuditContext(
            action="PERMISSION_GRANTED",
            entity_type="Role",
            entity_id=self.role_id,
            payload={"scope_key": self.scope_key, "role_name": self.role_name},
        )


@dataclass(frozen=True, kw_only=True)
class PermissionRevoked(DomainEvent):
    role_id: uuid.UUID
    role_name: str
    permission_id: uuid.UUID
    scope_key: str

    def to_audit_context(self) -> AuditContext:
        return AuditContext(
            action="PERMISSION_REVOKED",
            entity_type="Role",
            entity_id=self.role_id,
            payload={"scope_key": self.scope_key, "role_name": self.role_name},
        )


@dataclass(frozen=True, kw_only=True)
class UserRoleAssigned(DomainEvent):
    user_id: uuid.UUID
    user_name: str
    role_id: uuid.UUID
    role_name: str

    def to_audit_context(self) -> AuditContext:
        return AuditContext(
            action="USER_ROLE_ASSIGNED",
            entity_type="UserRole",
            entity_id=self.user_id,
            payload={"user": self.user_name, "role": self.role_name},
        )


@dataclass(frozen=True, kw_only=True)
class UserRoleRevoked(DomainEvent):
    user_id: uuid.UUID
    user_name: str
    role_id: uuid.UUID
    role_name: str

    def to_audit_context(self) -> AuditContext:
        return AuditContext(
            action="USER_ROLE_REVOKED",
            entity_type="UserRole",
            entity_id=self.user_id,
            payload={"user": self.user_name, "role": self.role_name},
        )
