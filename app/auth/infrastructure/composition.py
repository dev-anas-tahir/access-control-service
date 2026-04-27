from datetime import timedelta

from app.auth.application.use_cases.login import LoginUseCase
from app.auth.application.use_cases.logout import LogoutUseCase
from app.auth.application.use_cases.refresh_token import RefreshTokenUseCase
from app.auth.application.use_cases.signup import SignupUseCase
from app.auth.infrastructure.stores.redis_refresh_token_store import (
    RedisRefreshTokenStore,
)
from app.auth.infrastructure.stores.redis_revocation_store import RedisRevocationStore
from app.auth.infrastructure.unit_of_work import SqlAlchemyAuthUnitOfWork
from app.config import settings
from app.core.keys import key_pair
from app.db.redis import redis_client
from app.db.session import async_session_factory
from app.shared.infrastructure.crypto.bcrypt_password_hasher import BcryptPasswordHasher
from app.shared.infrastructure.crypto.jwt_token_issuer import JwtTokenIssuer
from app.shared.infrastructure.crypto.jwt_token_verifier import JwtTokenVerifier

# ── Shared singletons ────────────────────────────────────────────────────────
_hasher = BcryptPasswordHasher()
_token_issuer = JwtTokenIssuer(key_pair, settings.jwt_algorithm, settings.jwt_issuer)
_token_verifier = JwtTokenVerifier(key_pair, settings.jwt_algorithm)
_access_token_ttl = timedelta(minutes=settings.jwt_access_token_expire_minutes)
_refresh_token_ttl = timedelta(days=settings.jwt_refresh_token_expire_days)


def _uow_factory() -> SqlAlchemyAuthUnitOfWork:
    return SqlAlchemyAuthUnitOfWork(async_session_factory)


def _refresh_store() -> RedisRefreshTokenStore:
    return RedisRefreshTokenStore(redis_client)


def _revocation_store() -> RedisRevocationStore:
    return RedisRevocationStore(redis_client)


# ── Builders ─────────────────────────────────────────────────────────────────

def build_signup_use_case() -> SignupUseCase:
    return SignupUseCase(
        uow_factory=_uow_factory,
        hasher=_hasher,
    )


def build_login_use_case() -> LoginUseCase:
    return LoginUseCase(
        uow_factory=_uow_factory,
        hasher=_hasher,
        token_issuer=_token_issuer,
        refresh_store=_refresh_store(),
        access_token_ttl=_access_token_ttl,
        refresh_token_ttl=_refresh_token_ttl,
    )


def build_refresh_token_use_case() -> RefreshTokenUseCase:
    return RefreshTokenUseCase(
        uow_factory=_uow_factory,
        token_issuer=_token_issuer,
        refresh_store=_refresh_store(),
        access_token_ttl=_access_token_ttl,
        refresh_token_ttl=_refresh_token_ttl,
    )


def build_logout_use_case() -> LogoutUseCase:
    return LogoutUseCase(
        refresh_store=_refresh_store(),
        revocation_store=_revocation_store(),
    )


def build_token_verifier() -> JwtTokenVerifier:
    return _token_verifier


def build_revocation_store() -> RedisRevocationStore:
    return _revocation_store()


# ── FastAPI Depends providers ─────────────────────────────────────────────────

def get_signup_use_case() -> SignupUseCase:
    return build_signup_use_case()


def get_login_use_case() -> LoginUseCase:
    return build_login_use_case()


def get_refresh_token_use_case() -> RefreshTokenUseCase:
    return build_refresh_token_use_case()


def get_logout_use_case() -> LogoutUseCase:
    return build_logout_use_case()


def get_token_verifier() -> JwtTokenVerifier:
    return build_token_verifier()


def get_revocation_store() -> RedisRevocationStore:
    return build_revocation_store()
