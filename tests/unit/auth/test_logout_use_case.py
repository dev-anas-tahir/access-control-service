import time

from app.auth.application.dto import LogoutInput
from app.auth.application.use_cases.logout import LogoutUseCase
from tests.unit.auth.fakes import FakeRefreshTokenStore, FakeRevocationStore, make_user


def _make_use_case(
    refresh_store: FakeRefreshTokenStore,
    revocation_store: FakeRevocationStore,
) -> LogoutUseCase:
    return LogoutUseCase(
        refresh_store=refresh_store,
        revocation_store=revocation_store,
    )


async def test_logout_deletes_refresh_token():
    user = make_user()
    refresh_store = FakeRefreshTokenStore()
    await refresh_store.put("my_token", user.id, 7 * 86400)
    revocation_store = FakeRevocationStore()

    use_case = _make_use_case(refresh_store, revocation_store)
    future_exp = int(time.time()) + 900
    await use_case.execute(
        LogoutInput(refresh_token="my_token", jti="some-jti", exp=future_exp)
    )

    assert "my_token" not in refresh_store._store


async def test_logout_revokes_jti_with_remaining_ttl():
    refresh_store = FakeRefreshTokenStore()
    revocation_store = FakeRevocationStore()
    use_case = _make_use_case(refresh_store, revocation_store)

    future_exp = int(time.time()) + 500
    await use_case.execute(
        LogoutInput(refresh_token="tok", jti="jti-abc", exp=future_exp)
    )

    assert "jti-abc" in revocation_store._revoked
    assert 0 < revocation_store._revoked["jti-abc"] <= 500


async def test_logout_does_not_revoke_already_expired_token():
    refresh_store = FakeRefreshTokenStore()
    revocation_store = FakeRevocationStore()
    use_case = _make_use_case(refresh_store, revocation_store)

    past_exp = int(time.time()) - 60  # already expired
    await use_case.execute(
        LogoutInput(refresh_token="tok", jti="jti-expired", exp=past_exp)
    )

    assert "jti-expired" not in revocation_store._revoked
