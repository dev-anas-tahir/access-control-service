"""Audit logging handler for domain events.

This handler maps RBAC domain events to audit log entries,
decoupling the RBAC context from the Audit context via domain events.
"""

import uuid
from typing import Any

from app.rbac.domain.events import (
    PermissionGranted,
    PermissionRevoked,
    RoleCreated,
    RoleDeleted,
    UserRoleAssigned,
    UserRoleRevoked,
)
from app.shared.domain.events import DomainEvent
from app.shared.domain.ports.audit_logger import AuditLogger


class AuditLoggingHandler:
    """Handles RBAC domain events by creating audit log entries.

    This handler maps domain events to audit log entries, decoupling
    the RBAC bounded context from the Audit bounded context.
    """

    # Mapping of event types to (action, entity_type) tuples
    _EVENT_MAPPING: dict[type[DomainEvent], tuple[str, str]] = {
        RoleCreated: ("ROLE_CREATED", "Role"),
        RoleDeleted: ("ROLE_DELETED", "Role"),
        PermissionGranted: ("PERMISSION_GRANTED", "Role"),
        PermissionRevoked: ("PERMISSION_REVOKED", "Role"),
        UserRoleAssigned: ("USER_ROLE_ASSIGNED", "UserRole"),
        UserRoleRevoked: ("USER_ROLE_REVOKED", "UserRole"),
    }

    def __init__(self, audit_logger: AuditLogger) -> None:
        """Initialize with an audit logger implementation.

        Args:
            audit_logger: The audit logger port implementation to use
        """
        self._audit_logger = audit_logger

    async def handle(self, event: DomainEvent) -> None:
        """Handle a domain event by creating an audit log entry.

        Args:
            event: The domain event to handle

        Raises:
            ValueError: If the event type is not supported
        """
        event_type = type(event)
        if event_type not in self._EVENT_MAPPING:
            raise ValueError(f"Unsupported event type: {event_type.__name__}")

        action, entity_type = self._EVENT_MAPPING[event_type]
        entity_id = self._extract_entity_id(event)
        payload = self._extract_payload(event)

        await self._audit_logger.log(
            actor_id=event.actor_id or uuid.uuid4(),  # Fallback if actor_id is None
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
        )

    def _extract_entity_id(self, event: DomainEvent) -> uuid.UUID:
        """Extract the entity ID from a domain event.

        Args:
            event: The domain event

        Returns:
            The UUID of the affected entity
        """
        if isinstance(event, (RoleCreated, RoleDeleted)):
            return event.role_id
        elif isinstance(event, (PermissionGranted, PermissionRevoked)):
            return event.role_id
        elif isinstance(event, (UserRoleAssigned, UserRoleRevoked)):
            return event.user_id
        else:
            # Fallback to event_id if no specific entity_id
            return event.event_id

    def _extract_payload(self, event: DomainEvent) -> dict[str, Any]:
        """Extract the audit payload from a domain event.

        Args:
            event: The domain event

        Returns:
            Dictionary payload for audit logging
        """
        if hasattr(event, "to_audit_payload"):
            return event.to_audit_payload()
        return {}

    async def handle_many(self, events: list[DomainEvent]) -> None:
        """Handle multiple domain events.

        Args:
            events: List of domain events to handle
        """
        for event in events:
            await self.handle(event)
