from datetime import timedelta

import pytest

from app.auth.application.dto import RefreshInput
from app.auth.application.use_cases.refresh_token import RefreshTokenUseCase
from app.auth.domain.exceptions import InvalidCredentialsError, RefreshTokenInvalidError
from tests.unit.auth.fakes import (
    FakeAuthUnitOfWork,
    FakeRefreshTokenStore,
    FakeTokenIssuer,
    FakeUserRepository,
    make_user,
)

_TTL = timedelta(minutes=15)
_REFRESH_TTL = timedelta(days=7)


def _make_use_case(
    uow: FakeAuthUnitOfWork,
    refresh_store: FakeRefreshTokenStore,
) -> RefreshTokenUseCase:
    return RefreshTokenUseCase(
        uow_factory=lambda: uow,
        token_issuer=FakeTokenIssuer(token="new.access.token"),
        refresh_store=refresh_store,
        access_token_ttl=_TTL,
        refresh_token_ttl=_REFRESH_TTL,
    )


async def test_refresh_rotates_token_and_returns_new_pair():
    user = make_user()
    refresh_store = FakeRefreshTokenStore()
    await refresh_store.put("old_token", user.id, 7 * 86400)

    uow = FakeAuthUnitOfWork(users=FakeUserRepository([user]))
    use_case = _make_use_case(uow, refresh_store)

    result = await use_case.execute(RefreshInput(refresh_token="old_token"))

    assert result.access_token == "new.access.token"
    assert result.refresh_token != "old_token"
    assert result.refresh_token in refresh_store._store
    assert "old_token" not in refresh_store._store


async def test_refresh_raises_when_token_not_found():
    uow = FakeAuthUnitOfWork()
    refresh_store = FakeRefreshTokenStore()
    use_case = _make_use_case(uow, refresh_store)

    with pytest.raises(RefreshTokenInvalidError):
        await use_case.execute(RefreshInput(refresh_token="nonexistent"))


async def test_refresh_raises_when_user_not_found():
    refresh_store = FakeRefreshTokenStore()
    import uuid
    await refresh_store.put("valid_token", uuid.uuid4(), 7 * 86400)

    uow = FakeAuthUnitOfWork(users=FakeUserRepository([]))
    use_case = _make_use_case(uow, refresh_store)

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(RefreshInput(refresh_token="valid_token"))


async def test_refresh_raises_when_user_inactive():
    user = make_user(is_active=False)
    refresh_store = FakeRefreshTokenStore()
    await refresh_store.put("valid_token", user.id, 7 * 86400)

    uow = FakeAuthUnitOfWork(users=FakeUserRepository([user]))
    use_case = _make_use_case(uow, refresh_store)

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(RefreshInput(refresh_token="valid_token"))
