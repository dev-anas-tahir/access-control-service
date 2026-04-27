"""In-memory fakes for audit ports — use in unit tests."""

import uuid
from datetime import datetime, timezone

from app.shared.domain.entities.audit_log import AuditLog


def make_audit_log(
    action: str = "ROLE_CREATED",
    entity_type: str = "Role",
) -> AuditLog:
    return AuditLog(
        id=uuid.uuid4(),
        actor_id=uuid.uuid4(),
        action=action,
        entity_type=entity_type,
        entity_id=uuid.uuid4(),
        payload={"detail": "test"},
        created_at=datetime.now(timezone.utc),
    )


class FakeAuditLogReader:
    def __init__(self, logs: list[AuditLog] | None = None) -> None:
        self._logs = logs or []

    async def list_paginated(self, *, page: int, page_size: int) -> list[AuditLog]:
        start = (page - 1) * page_size
        return self._logs[start : start + page_size]
