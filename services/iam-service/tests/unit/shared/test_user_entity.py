import uuid

from app.shared.domain.entities.user import User


def _user(is_active: bool) -> User:
    return User(
        id=uuid.uuid4(),
        username="alice",
        password_hash="x",
        is_active=is_active,
        is_super_user=False,
    )


def test_active_user_is_authenticatable():
    assert _user(is_active=True).is_authenticatable() is True


def test_inactive_user_is_not_authenticatable():
    assert _user(is_active=False).is_authenticatable() is False
