from datetime import datetime, timezone

from app.auth.application.dto import LogoutInput
from app.auth.domain.ports.refresh_token_store import RefreshTokenStore
from app.auth.domain.ports.revocation_store import RevocationStore


class LogoutUseCase:
    def __init__(
        self,
        refresh_store: RefreshTokenStore,
        revocation_store: RevocationStore,
    ) -> None:
        self._refresh_store = refresh_store
        self._revocation_store = revocation_store

    async def execute(self, input: LogoutInput) -> None:
        await self._refresh_store.delete(input.refresh_token)

        now = int(datetime.now(timezone.utc).timestamp())
        ttl = max(input.exp - now, 0)
        if ttl > 0:
            await self._revocation_store.revoke(input.jti, ttl)
