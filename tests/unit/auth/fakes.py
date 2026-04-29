"""In-memory fakes for all auth ports — use in unit tests."""

import uuid
from dataclasses import dataclass, field

from app.auth.domain.ports.token_issuer import TokenClaims
from app.shared.domain.entities.permission import Permission
from app.shared.domain.entities.role import Role
from app.shared.domain.entities.user import User
from app.shared.domain.values.email import Email
from app.shared.domain.values.scope_key import ScopeKey

# ── Entity factories ──────────────────────────────────────────────────────────

def make_permission(scope_key: str = "resource:read") -> Permission:
    return Permission(
        id=uuid.uuid4(),
        scope_key=ScopeKey.parse(scope_key),
    )


def make_role(
    name: str = "viewer", permissions: list[Permission] | None = None
) -> Role:
    return Role(id=uuid.uuid4(), name=name, permissions=permissions or [])


def make_user(
    *,
    username: str = "testuser",
    password_hash: str = "hashed_Password1!",
    is_active: bool = True,
    is_super_user: bool = False,
    roles: list[Role] | None = None,
    email: str | None = None,
) -> User:
    return User(
        id=uuid.uuid4(),
        username=username,
        email=Email(email) if email else None,
        password_hash=password_hash,
        is_active=is_active,
        is_super_user=is_super_user,
        roles=roles if roles is not None else [make_role()],
    )


# ── Repository fakes ──────────────────────────────────────────────────────────

class FakeUserRepository:
    def __init__(self, seed: list[User] | None = None) -> None:
        self._store: dict[uuid.UUID, User] = {u.id: u for u in (seed or [])}

    async def find_by_username(self, username: str) -> User | None:
        return next((u for u in self._store.values() if u.username == username), None)

    async def find_by_email(self, email: str) -> User | None:
        return next(
            (u for u in self._store.values() if u.email and u.email.value == email),
            None,
        )

    async def find_by_id(self, id: uuid.UUID) -> User | None:
        return self._store.get(id)

    async def add(self, user: User) -> User:
        self._store[user.id] = user
        return user

    async def update(self, user: User) -> None:
        self._store[user.id] = user


class FakeRoleRepository:
    def __init__(self, roles: list[Role] | None = None) -> None:
        self._store: dict[str, Role] = {r.name: r for r in (roles or [])}

    async def find_by_name(self, name: str) -> Role | None:
        return self._store.get(name)


# ── Unit of Work fake ─────────────────────────────────────────────────────────

class FakeAuthUnitOfWork:
    def __init__(
        self,
        users: FakeUserRepository | None = None,
        roles: FakeRoleRepository | None = None,
    ) -> None:
        self.users = users or FakeUserRepository()
        self.roles = roles or FakeRoleRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> "FakeAuthUnitOfWork":
        return self

    async def __aexit__(self, exc_type: object, *args: object) -> None:
        if exc_type:
            self.rolled_back = True

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


# ── Token store fakes ─────────────────────────────────────────────────────────

class FakeRefreshTokenStore:
    def __init__(self) -> None:
        self._store: dict[str, uuid.UUID] = {}

    async def put(self, token: str, user_id: uuid.UUID, ttl_seconds: int) -> None:
        self._store[token] = user_id

    async def get(self, token: str) -> uuid.UUID | None:
        return self._store.get(token)

    async def delete(self, token: str) -> None:
        self._store.pop(token, None)


class FakeRevocationStore:
    def __init__(self) -> None:
        self._revoked: dict[str, int] = {}  # jti -> ttl

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        self._revoked[jti] = ttl_seconds

    async def is_revoked(self, jti: str) -> bool:
        return jti in self._revoked


# ── Crypto fakes ──────────────────────────────────────────────────────────────

@dataclass
class FakePasswordHasher:
    verify_returns: bool = True
    needs_rehash_returns: bool = False

    def hash(self, plain: str) -> str:
        return f"hashed:{plain}"

    def verify(self, plain: str, hashed: str) -> bool:
        return self.verify_returns

    def needs_rehash(self, hashed: str) -> bool:
        return self.needs_rehash_returns


@dataclass
class FakeTokenIssuer:
    token: str = "fake.access.token"

    def issue(self, claims: TokenClaims) -> str:
        return self.token


@dataclass
class FakeTokenVerifier:
    payload: dict[str, object] = field(
        default_factory=lambda: {
            "sub": str(uuid.uuid4()),
            "jti": str(uuid.uuid4()),
            "exp": 9999999999,
            "iat": 0,
            "iss": "test",
            "username": "testuser",
            "roles": [],
            "permissions": [],
            "is_super_user": False,
        }
    )
    raises: type[Exception] | None = None

    def verify(self, token: str) -> dict[str, object]:
        if self.raises:
            raise self.raises()
        return self.payload
