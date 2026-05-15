import secrets
from datetime import timedelta

from app.auth.application.dto import RefreshInput, RefreshResult
from app.auth.domain.exceptions import InvalidCredentialsError, RefreshTokenInvalidError
from app.auth.domain.ports.refresh_token_store import RefreshTokenStore
from app.auth.domain.ports.token_issuer import TokenClaims, TokenIssuer
from app.auth.domain.ports.unit_of_work import AuthUnitOfWorkFactory


class RefreshTokenUseCase:
    def __init__(
        self,
        uow_factory: AuthUnitOfWorkFactory,
        token_issuer: TokenIssuer,
        refresh_store: RefreshTokenStore,
        access_token_ttl: timedelta,
        refresh_token_ttl: timedelta,
    ) -> None:
        self._uow_factory = uow_factory
        self._token_issuer = token_issuer
        self._refresh_store = refresh_store
        self._access_token_ttl = access_token_ttl
        self._refresh_token_ttl = refresh_token_ttl

    async def execute(self, input: RefreshInput) -> RefreshResult:
        user_id = await self._refresh_store.get(input.refresh_token)
        if not user_id:
            raise RefreshTokenInvalidError()

        async with self._uow_factory() as uow:
            user = await uow.users.find_by_id(user_id)
            if not user or not user.is_authenticatable():
                raise InvalidCredentialsError()

            access_token = self._token_issuer.issue(
                TokenClaims(
                    sub=user.id,
                    username=user.username,
                    roles=[role.name for role in user.roles],
                    permissions=[
                        perm.scope_key.key
                        for role in user.roles
                        for perm in role.permissions
                    ],
                    is_super_user=user.is_super_user,
                    ttl=self._access_token_ttl,
                )
            )

        await self._refresh_store.delete(input.refresh_token)

        new_refresh_token = secrets.token_urlsafe(64)
        ttl_seconds = int(self._refresh_token_ttl.total_seconds())
        await self._refresh_store.put(new_refresh_token, user.id, ttl_seconds)

        return RefreshResult(access_token=access_token, refresh_token=new_refresh_token)
