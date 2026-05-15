import uuid

import pytest

from app.rbac.application.dto import AssignRoleToUserInput
from app.rbac.application.use_cases.assign_role_to_user import AssignRoleToUserUseCase
from app.rbac.domain.events import UserRoleAssigned
from app.rbac.domain.exceptions import RoleNotFoundError, UserNotFoundError
from tests.unit.rbac.fakes import (
    FakeRbacUnitOfWork,
    FakeRoleRepository,
    FakeUserReader,
    make_role,
    make_user_summary,
)


def _make_use_case(uow: FakeRbacUnitOfWork) -> AssignRoleToUserUseCase:
    return AssignRoleToUserUseCase(uow_factory=lambda: uow)


async def test_assign_role_to_user_success():
    user = make_user_summary()
    role = make_role()
    uow = FakeRbacUnitOfWork(
        roles=FakeRoleRepository([role]),
        users=FakeUserReader([user]),
    )
    use_case = _make_use_case(uow)

    result = await use_case.execute(
        AssignRoleToUserInput(
            user_id=user.id, role_id=role.id, actor_id=uuid.uuid4()
        )
    )

    assert result.user_id == user.id
    assert result.role_id == role.id
    assert await uow.assignments.role_has_permission(user.id, role.id) is False
    assert (user.id, role.id) in uow.assignments._user_roles
    assert uow.committed is True


async def test_assign_role_to_user_emits_domain_event():
    user = make_user_summary(username="bob")
    role = make_role(name="analyst")
    uow = FakeRbacUnitOfWork(
        roles=FakeRoleRepository([role]),
        users=FakeUserReader([user]),
    )
    use_case = _make_use_case(uow)

    await use_case.execute(
        AssignRoleToUserInput(
            user_id=user.id, role_id=role.id, actor_id=uuid.uuid4()
        )
    )

    events = uow.emitted_events
    assert len(events) == 1
    event = events[0]
    assert isinstance(event, UserRoleAssigned)
    assert event.user_name == "bob"
    assert event.role_name == "analyst"


async def test_assign_role_raises_when_user_not_found():
    role = make_role()
    uow = FakeRbacUnitOfWork(roles=FakeRoleRepository([role]))
    use_case = _make_use_case(uow)

    with pytest.raises(UserNotFoundError):
        await use_case.execute(
            AssignRoleToUserInput(
                user_id=uuid.uuid4(), role_id=role.id, actor_id=uuid.uuid4()
            )
        )


async def test_assign_role_raises_when_role_not_found():
    user = make_user_summary()
    uow = FakeRbacUnitOfWork(users=FakeUserReader([user]))
    use_case = _make_use_case(uow)

    with pytest.raises(RoleNotFoundError):
        await use_case.execute(
            AssignRoleToUserInput(
                user_id=user.id, role_id=uuid.uuid4(), actor_id=uuid.uuid4()
            )
        )
