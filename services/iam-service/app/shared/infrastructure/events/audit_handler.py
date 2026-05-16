"""Audit logging handler for domain events."""

import uuid

from app.shared.domain.events import DomainEvent
from app.shared.domain.ports.audit_logger import AuditLogger


class AuditLoggingHandler:
    """Routes auditable domain events to the audit logger.

    Events supply all audit-relevant facts via to_audit_context(); this
    handler knows nothing about concrete event types.
    """

    def __init__(self, audit_logger: AuditLogger) -> None:
        self._audit_logger = audit_logger

    async def handle(self, event: DomainEvent) -> None:
        ctx = event.to_audit_context()
        await self._audit_logger.log(
            actor_id=event.actor_id or uuid.uuid4(),
            action=ctx.action,
            entity_type=ctx.entity_type,
            entity_id=ctx.entity_id,
            payload=ctx.payload,
        )

    async def handle_many(self, events: list[DomainEvent]) -> None:
        for event in events:
            await self.handle(event)
