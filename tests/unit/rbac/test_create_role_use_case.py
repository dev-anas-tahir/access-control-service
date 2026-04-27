import uuid

import pytest

from app.rbac.application.dto import CreateRoleInput
from app.rbac.application.use_cases.create_role import CreateRoleUseCase
from app.rbac.domain.exceptions import RoleAlreadyExistsError
from tests.unit.rbac.fakes import FakeRbacUnitOfWork, make_role


def _uow_factory(**kwargs):
    uow = FakeRbacUnitOfWork(**kwargs)
    return lambda: uow, uow


async def test_create_role_success():
    factory, uow = _uow_factory()
    use_case = CreateRoleUseCase(uow_factory=factory)
    actor_id = uuid.uuid4()

    result = await use_case.execute(
        CreateRoleInput(name="analyst", description="BI team", actor_id=actor_id)
    )

    assert result.name == "analyst"
    assert result.description == "BI team"
    assert result.is_system is False
    assert result.created_by == actor_id
    assert uow.committed is True


async def test_create_role_logs_audit_event():
    factory, uow = _uow_factory()
    use_case = CreateRoleUseCase(uow_factory=factory)
    actor_id = uuid.uuid4()

    await use_case.execute(
        CreateRoleInput(name="analyst", description=None, actor_id=actor_id)
    )

    assert len(uow.audit_logger.entries) == 1
    entry = uow.audit_logger.entries[0]
    assert entry.action == "ROLE_CREATED"
    assert entry.actor_id == actor_id
    assert entry.entity_type == "Role"


async def test_create_role_raises_when_name_taken():
    existing = make_role(name="editor")
    from tests.unit.rbac.fakes import FakeRoleRepository

    factory, uow = _uow_factory(roles=FakeRoleRepository([existing]))
    use_case = CreateRoleUseCase(uow_factory=factory)

    with pytest.raises(RoleAlreadyExistsError):
        await use_case.execute(
            CreateRoleInput(name="editor", description=None, actor_id=uuid.uuid4())
        )

    assert uow.committed is False
