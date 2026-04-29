import uuid

import pytest

from app.rbac.application.dto import DeleteRoleInput
from app.rbac.application.use_cases.delete_role import DeleteRoleUseCase
from app.rbac.domain.exceptions import RoleNotFoundError
from app.shared.domain.exceptions import SystemRoleProtectedError
from tests.unit.rbac.fakes import FakeRbacUnitOfWork, FakeRoleRepository, make_role


def _make_use_case(uow: FakeRbacUnitOfWork) -> DeleteRoleUseCase:
    return DeleteRoleUseCase(uow_factory=lambda: uow)


async def test_delete_role_success():
    role = make_role(name="analyst", is_system=False)
    uow = FakeRbacUnitOfWork(roles=FakeRoleRepository([role]))
    use_case = _make_use_case(uow)

    await use_case.execute(
        DeleteRoleInput(role_id=role.id, actor_id=uuid.uuid4())
    )

    stored = await uow.roles.find_by_id(role.id)
    assert stored is not None
    assert stored.is_deleted is True
    assert stored.deleted_at is not None
    assert uow.committed is True


async def test_delete_role_logs_audit_event():
    role = make_role(name="analyst")
    uow = FakeRbacUnitOfWork(roles=FakeRoleRepository([role]))
    use_case = _make_use_case(uow)

    await use_case.execute(DeleteRoleInput(role_id=role.id, actor_id=uuid.uuid4()))

    assert len(uow.audit_logger.entries) == 1
    assert uow.audit_logger.entries[0].action == "ROLE_DELETED"


async def test_delete_role_raises_when_not_found():
    uow = FakeRbacUnitOfWork()
    use_case = _make_use_case(uow)

    with pytest.raises(RoleNotFoundError):
        await use_case.execute(
            DeleteRoleInput(role_id=uuid.uuid4(), actor_id=uuid.uuid4())
        )


async def test_delete_role_raises_for_system_role():
    role = make_role(name="admin", is_system=True)
    uow = FakeRbacUnitOfWork(roles=FakeRoleRepository([role]))
    use_case = _make_use_case(uow)

    with pytest.raises(SystemRoleProtectedError):
        await use_case.execute(DeleteRoleInput(role_id=role.id, actor_id=uuid.uuid4()))

    assert uow.committed is False
