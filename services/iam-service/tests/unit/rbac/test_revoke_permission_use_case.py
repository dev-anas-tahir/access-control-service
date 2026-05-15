import uuid

import pytest

from app.rbac.application.dto import RevokePermissionInput
from app.rbac.application.use_cases.revoke_permission import RevokePermissionUseCase
from app.rbac.domain.events import PermissionRevoked
from app.rbac.domain.exceptions import PermissionNotFoundError, RoleNotFoundError
from tests.unit.rbac.fakes import (
    FakeAssignmentRepository,
    FakePermissionRepository,
    FakeRbacUnitOfWork,
    FakeRoleRepository,
    make_permission,
    make_role,
)


def _make_use_case(uow: FakeRbacUnitOfWork) -> RevokePermissionUseCase:
    return RevokePermissionUseCase(uow_factory=lambda: uow)


async def test_revoke_permission_success():
    role = make_role()
    perm = make_permission(resource="reports", action="read")
    assignments = FakeAssignmentRepository()
    await assignments.assign_permission(
        role_id=role.id, permission_id=perm.id, granted_by=uuid.uuid4()
    )
    uow = FakeRbacUnitOfWork(
        roles=FakeRoleRepository([role]),
        permissions=FakePermissionRepository([perm]),
        assignments=assignments,
    )
    use_case = _make_use_case(uow)

    await use_case.execute(
        RevokePermissionInput(
            role_id=role.id, scope_key="reports:read", actor_id=uuid.uuid4()
        )
    )

    assert not await assignments.role_has_permission(role.id, perm.id)
    assert uow.committed is True


async def test_revoke_permission_emits_domain_event():
    role = make_role()
    perm = make_permission(resource="reports", action="read")
    uow = FakeRbacUnitOfWork(
        roles=FakeRoleRepository([role]),
        permissions=FakePermissionRepository([perm]),
    )
    use_case = _make_use_case(uow)

    await use_case.execute(
        RevokePermissionInput(
            role_id=role.id, scope_key="reports:read", actor_id=uuid.uuid4()
        )
    )

    events = uow.emitted_events
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, PermissionRevoked)
    assert event.scope_key == "reports:read"


async def test_revoke_permission_raises_when_role_not_found():
    uow = FakeRbacUnitOfWork()
    use_case = _make_use_case(uow)

    with pytest.raises(RoleNotFoundError):
        await use_case.execute(
            RevokePermissionInput(
                role_id=uuid.uuid4(), scope_key="reports:read", actor_id=uuid.uuid4()
            )
        )


async def test_revoke_permission_raises_when_permission_not_found():
    role = make_role()
    uow = FakeRbacUnitOfWork(roles=FakeRoleRepository([role]))
    use_case = _make_use_case(uow)

    with pytest.raises(PermissionNotFoundError):
        await use_case.execute(
            RevokePermissionInput(
                role_id=role.id, scope_key="nonexistent:action", actor_id=uuid.uuid4()
            )
        )
