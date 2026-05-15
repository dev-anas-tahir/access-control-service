from typing import Callable, Protocol

from app.auth.domain.ports.role_repository import RoleRepository
from app.auth.domain.ports.user_repository import UserRepository


class AuthUnitOfWork(Protocol):
    users: UserRepository
    roles: RoleRepository

    async def __aenter__(self) -> "AuthUnitOfWork": ...

    async def __aexit__(self, *args: object) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


AuthUnitOfWorkFactory = Callable[[], AuthUnitOfWork]
