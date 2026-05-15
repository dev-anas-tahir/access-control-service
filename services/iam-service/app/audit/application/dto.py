from dataclasses import dataclass

from app.shared.domain.entities.audit_log import AuditLog


@dataclass
class GetAuditLogsInput:
    page: int = 1
    page_size: int = 20


@dataclass
class GetAuditLogsResult:
    items: list[AuditLog]
