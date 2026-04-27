from app.audit.application.use_cases.get_audit_logs import GetAuditLogsUseCase
from app.audit.infrastructure.sqlalchemy_audit_log_reader import (
    SqlAlchemyAuditLogReader,
)
from app.db.session import async_session_factory


def get_audit_logs_use_case() -> GetAuditLogsUseCase:
    reader = SqlAlchemyAuditLogReader(async_session_factory)
    return GetAuditLogsUseCase(reader=reader)
