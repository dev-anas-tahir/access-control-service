from app.audit.application.dto import GetAuditLogsInput, GetAuditLogsResult
from app.audit.domain.ports.audit_log_reader import AuditLogReader


class GetAuditLogsUseCase:
    def __init__(self, reader: AuditLogReader) -> None:
        self._reader = reader

    async def execute(self, input: GetAuditLogsInput) -> GetAuditLogsResult:
        items = await self._reader.list_paginated(
            page=input.page, page_size=input.page_size
        )
        return GetAuditLogsResult(items=items)
