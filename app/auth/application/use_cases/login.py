import secrets
from datetime import timedelta

from app.auth.application.dto import LoginInput, LoginResult
from app.auth.domain.exceptions import InvalidCredentialsError
from app.auth.domain.ports.password_hasher import PasswordHasher
from app.auth.domain.ports.refresh_token_store import RefreshTokenStore
from app.auth.domain.ports.token_issuer import TokenClaims, TokenIssuer
from app.auth.domain.ports.unit_of_work import AuthUnitOfWorkFactory


class LoginUseCase:
    def __init__(
        self,
        uow_factory: AuthUnitOfWorkFactory,
        hasher: PasswordHasher,
        token_issuer: TokenIssuer,
        refresh_store: RefreshTokenStore,
        access_token_ttl: timedelta,
        refresh_token_ttl: timedelta,
    ) -> None:
        self._uow_factory = uow_factory
        self._hasher = hasher
        self._token_issuer = token_issuer
        self._refresh_store = refresh_store
        self._access_token_ttl = access_token_ttl
        self._refresh_token_ttl = refresh_token_ttl

    async def execute(self, input: LoginInput) -> LoginResult:
        async with self._uow_factory() as uow:
            user = await uow.users.find_by_username(input.username)
            if not user or not user.is_authenticatable():
                raise InvalidCredentialsError()

            if not self._hasher.verify(input.password, user.password_hash):
                raise InvalidCredentialsError()

            if self._hasher.needs_rehash(user.password_hash):
                user.password_hash = self._hasher.hash(input.password)
                await uow.users.update(user)

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

            await uow.commit()

        refresh_token = secrets.token_urlsafe(64)
        ttl_seconds = int(self._refresh_token_ttl.total_seconds())
        await self._refresh_store.put(refresh_token, user.id, ttl_seconds)

        return LoginResult(access_token=access_token, refresh_token=refresh_token)
