import uuid

import pytest

from app.shared.domain.entities.role import Role
from app.shared.domain.exceptions import SystemRoleProtectedError


def _role(is_system: bool) -> Role:
    return Role(id=uuid.uuid4(), name="r", is_system=is_system)


def test_assert_deletable_passes_for_non_system_role():
    _role(is_system=False).assert_deletable()


def test_assert_deletable_raises_for_system_role():
    with pytest.raises(SystemRoleProtectedError):
        _role(is_system=True).assert_deletable()
