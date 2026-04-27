import uuid

import pytest

from app.rbac.application.dto import AssignPermissionInput
from app.rbac.application.use_cases.assign_permission import AssignPermissionUseCase
from app.rbac.domain.exceptions import PermissionAlreadyAssignedError, RoleNotFoundError
from tests.unit.rbac.fakes import (
    FakeAssignmentRepository,
    FakePermissionRepository,
    FakeRbacUnitOfWork,
    FakeRoleRepository,
    make_permission,
    make_role,
)


def _make_use_case(uow: FakeRbacUnitOfWork) -> AssignPermissionUseCase:
    return AssignPermissionUseCase(uow_factory=lambda: uow)


async def test_assign_permission_creates_permission_and_assigns():
    role = make_role()
    uow = FakeRbacUnitOfWork(roles=FakeRoleRepository([role]))
    use_case = _make_use_case(uow)

    result = await use_case.execute(
        AssignPermissionInput(
            role_id=role.id,
            resource="reports",
            action="read",
            actor_id=uuid.uuid4(),
        )
    )

    assert result.role_id == role.id
    perm = await uow.permissions.find_by_scope_key("reports:read")
    assert perm is not None
    assert await uow.assignments.role_has_permission(role.id, perm.id)
    assert uow.committed is True


async def test_assign_permission_reuses_existing_permission():
    role = make_role()
    existing_perm = make_permission(resource="reports", action="read")
    uow = FakeRbacUnitOfWork(
        roles=FakeRoleRepository([role]),
        permissions=FakePermissionRepository([existing_perm]),
    )
    use_case = _make_use_case(uow)

    result = await use_case.execute(
        AssignPermissionInput(
            role_id=role.id,
            resource="reports",
            action="read",
            actor_id=uuid.uuid4(),
        )
    )

    assert result.permission_id == existing_perm.id


async def test_assign_permission_raises_when_role_not_found():
    uow = FakeRbacUnitOfWork()
    use_case = _make_use_case(uow)

    with pytest.raises(RoleNotFoundError):
        await use_case.execute(
            AssignPermissionInput(
                role_id=uuid.uuid4(),
                resource="reports",
                action="read",
                actor_id=uuid.uuid4(),
            )
        )


async def test_assign_permission_raises_when_already_assigned():
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

    with pytest.raises(PermissionAlreadyAssignedError):
        await use_case.execute(
            AssignPermissionInput(
                role_id=role.id,
                resource="reports",
                action="read",
                actor_id=uuid.uuid4(),
            )
        )


async def test_assign_permission_logs_audit_event():
    role = make_role()
    uow = FakeRbacUnitOfWork(roles=FakeRoleRepository([role]))
    use_case = _make_use_case(uow)

    await use_case.execute(
        AssignPermissionInput(
            role_id=role.id,
            resource="reports",
            action="read",
            actor_id=uuid.uuid4(),
        )
    )

    assert len(uow.audit_logger.entries) == 1
    assert uow.audit_logger.entries[0].action == "PERMISSION_GRANTED"
