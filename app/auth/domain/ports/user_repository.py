import uuid
from typing import Protocol

from app.shared.domain.entities.user import User


class UserRepository(Protocol):
    """Port for user persistence.

    Implementations must eagerly load User.roles and Role.permissions before
    returning — callers must not trigger lazy loads after the session closes.
    """

    async def find_by_username(self, username: str) -> User | None: ...

    async def find_by_email(self, email: str) -> User | None: ...

    async def find_by_id(self, id: uuid.UUID) -> User | None: ...

    async def add(self, user: User) -> User:
        """Persist a new user and return it with its DB-assigned id."""
        ...

    async def update(self, user: User) -> None: ...
