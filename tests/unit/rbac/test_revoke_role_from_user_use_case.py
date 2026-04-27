import uuid

import pytest

from app.rbac.application.dto import RevokeRoleFromUserInput
from app.rbac.application.use_cases.revoke_role_from_user import (
    RevokeRoleFromUserUseCase,
)
from app.rbac.domain.exceptions import RoleNotFoundError, UserNotFoundError
from tests.unit.rbac.fakes import (
    FakeAssignmentRepository,
    FakeRbacUnitOfWork,
    FakeRoleRepository,
    FakeUserReader,
    make_role,
    make_user_summary,
)


def _make_use_case(uow: FakeRbacUnitOfWork) -> RevokeRoleFromUserUseCase:
    return RevokeRoleFromUserUseCase(uow_factory=lambda: uow)


async def test_revoke_role_from_user_success():
    user = make_user_summary()
    role = make_role()
    assignments = FakeAssignmentRepository()
    await assignments.assign_role_to_user(
        user_id=user.id, role_id=role.id, assigned_by=uuid.uuid4()
    )
    uow = FakeRbacUnitOfWork(
        roles=FakeRoleRepository([role]),
        users=FakeUserReader([user]),
        assignments=assignments,
    )
    use_case = _make_use_case(uow)

    await use_case.execute(
        RevokeRoleFromUserInput(
            user_id=user.id, role_id=role.id, actor_id=uuid.uuid4()
        )
    )

    assert (user.id, role.id) not in assignments._user_roles
    assert uow.committed is True


async def test_revoke_role_from_user_logs_audit_event():
    user = make_user_summary(username="carol")
    role = make_role(name="editor")
    uow = FakeRbacUnitOfWork(
        roles=FakeRoleRepository([role]),
        users=FakeUserReader([user]),
    )
    use_case = _make_use_case(uow)

    await use_case.execute(
        RevokeRoleFromUserInput(
            user_id=user.id, role_id=role.id, actor_id=uuid.uuid4()
        )
    )

    assert len(uow.audit_logger.entries) == 1
    entry = uow.audit_logger.entries[0]
    assert entry.action == "USER_ROLE_REVOKED"
    assert entry.payload == {"user": "carol", "role": "editor"}


async def test_revoke_role_raises_when_user_not_found():
    role = make_role()
    uow = FakeRbacUnitOfWork(roles=FakeRoleRepository([role]))
    use_case = _make_use_case(uow)

    with pytest.raises(UserNotFoundError):
        await use_case.execute(
            RevokeRoleFromUserInput(
                user_id=uuid.uuid4(), role_id=role.id, actor_id=uuid.uuid4()
            )
        )


async def test_revoke_role_raises_when_role_not_found():
    user = make_user_summary()
    uow = FakeRbacUnitOfWork(users=FakeUserReader([user]))
    use_case = _make_use_case(uow)

    with pytest.raises(RoleNotFoundError):
        await use_case.execute(
            RevokeRoleFromUserInput(
                user_id=user.id, role_id=uuid.uuid4(), actor_id=uuid.uuid4()
            )
        )
