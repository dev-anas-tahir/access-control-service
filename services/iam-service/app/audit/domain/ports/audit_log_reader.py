from typing import Protocol

from app.shared.domain.entities.audit_log import AuditLog


class AuditLogReader(Protocol):
    async def list_paginated(
        self, *, page: int, page_size: int
    ) -> list[AuditLog]: ...
