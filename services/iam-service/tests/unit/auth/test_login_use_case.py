from datetime import timedelta

import pytest

from app.auth.application.dto import LoginInput
from app.auth.application.use_cases.login import LoginUseCase
from app.auth.domain.exceptions import InvalidCredentialsError
from tests.unit.auth.fakes import (
    FakeAuthUnitOfWork,
    FakePasswordHasher,
    FakeRefreshTokenStore,
    FakeTokenIssuer,
    FakeUserRepository,
    make_user,
)

_TTL = timedelta(minutes=15)
_REFRESH_TTL = timedelta(days=7)


def _make_use_case(
    uow: FakeAuthUnitOfWork,
    hasher: FakePasswordHasher | None = None,
    refresh_store: FakeRefreshTokenStore | None = None,
) -> LoginUseCase:
    return LoginUseCase(
        uow_factory=lambda: uow,
        hasher=hasher or FakePasswordHasher(verify_returns=True),
        token_issuer=FakeTokenIssuer(token="access.token"),
        refresh_store=refresh_store or FakeRefreshTokenStore(),
        access_token_ttl=_TTL,
        refresh_token_ttl=_REFRESH_TTL,
    )


async def test_login_returns_tokens_on_valid_credentials():
    user = make_user(username="alice")
    refresh_store = FakeRefreshTokenStore()
    uow = FakeAuthUnitOfWork(users=FakeUserRepository([user]))
    use_case = _make_use_case(uow, refresh_store=refresh_store)

    result = await use_case.execute(LoginInput(username="alice", password="Secret1!"))

    assert result.access_token == "access.token"
    assert result.refresh_token in refresh_store._store
    assert refresh_store._store[result.refresh_token] == user.id


async def test_login_raises_when_user_not_found():
    uow = FakeAuthUnitOfWork(users=FakeUserRepository([]))
    use_case = _make_use_case(uow)

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(LoginInput(username="nobody", password="Secret1!"))


async def test_login_raises_when_user_inactive():
    user = make_user(username="alice", is_active=False)
    uow = FakeAuthUnitOfWork(users=FakeUserRepository([user]))
    use_case = _make_use_case(uow)

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(LoginInput(username="alice", password="Secret1!"))


async def test_login_raises_when_wrong_password():
    user = make_user(username="alice")
    uow = FakeAuthUnitOfWork(users=FakeUserRepository([user]))
    use_case = _make_use_case(uow, hasher=FakePasswordHasher(verify_returns=False))

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(LoginInput(username="alice", password="wrong"))


async def test_login_rehashes_password_when_needed():
    user = make_user(username="alice", password_hash="old_django_hash")
    uow = FakeAuthUnitOfWork(users=FakeUserRepository([user]))
    hasher = FakePasswordHasher(verify_returns=True, needs_rehash_returns=True)
    use_case = _make_use_case(uow, hasher=hasher)

    await use_case.execute(LoginInput(username="alice", password="Secret1!"))

    updated = await uow.users.find_by_username("alice")
    assert updated is not None
    assert updated.password_hash == "hashed:Secret1!"
    assert uow.committed


async def test_login_commits_on_success():
    user = make_user(username="alice")
    uow = FakeAuthUnitOfWork(users=FakeUserRepository([user]))
    use_case = _make_use_case(uow)

    await use_case.execute(LoginInput(username="alice", password="Secret1!"))

    assert uow.committed
