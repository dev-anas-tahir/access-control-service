from app.audit.application.dto import GetAuditLogsInput
from app.audit.application.use_cases.get_audit_logs import GetAuditLogsUseCase
from tests.unit.audit.fakes import FakeAuditLogReader, make_audit_log


async def test_returns_empty_when_no_logs():
    use_case = GetAuditLogsUseCase(reader=FakeAuditLogReader())

    result = await use_case.execute(GetAuditLogsInput(page=1, page_size=20))

    assert result.items == []


async def test_returns_all_logs_within_page():
    logs = [make_audit_log() for _ in range(3)]
    use_case = GetAuditLogsUseCase(reader=FakeAuditLogReader(logs))

    result = await use_case.execute(GetAuditLogsInput(page=1, page_size=20))

    assert len(result.items) == 3
    assert result.items == logs


async def test_pagination_first_page():
    logs = [make_audit_log(action=f"ACTION_{i}") for i in range(5)]
    use_case = GetAuditLogsUseCase(reader=FakeAuditLogReader(logs))

    result = await use_case.execute(GetAuditLogsInput(page=1, page_size=2))

    assert len(result.items) == 2
    assert result.items == logs[:2]


async def test_pagination_second_page():
    logs = [make_audit_log(action=f"ACTION_{i}") for i in range(5)]
    use_case = GetAuditLogsUseCase(reader=FakeAuditLogReader(logs))

    result = await use_case.execute(GetAuditLogsInput(page=2, page_size=2))

    assert len(result.items) == 2
    assert result.items == logs[2:4]


async def test_pagination_beyond_last_page_returns_empty():
    logs = [make_audit_log() for _ in range(3)]
    use_case = GetAuditLogsUseCase(reader=FakeAuditLogReader(logs))

    result = await use_case.execute(GetAuditLogsInput(page=10, page_size=20))

    assert result.items == []
