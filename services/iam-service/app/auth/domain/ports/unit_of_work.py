from typing import Callable, Protocol

from app.auth.domain.ports.role_repository import RoleRepository
from app.auth.domain.ports.user_repository import UserRepository
from app.shared.domain.events import DomainEvent


class AuthUnitOfWork(Protocol):
    users: UserRepository
    roles: RoleRepository

    async def __aenter__(self) -> "AuthUnitOfWork": ...

    async def __aexit__(self, *args: object) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    def add_event(self, event: DomainEvent) -> None: ...

    def collect_events(self) -> list[DomainEvent]: ...


AuthUnitOfWorkFactory = Callable[[], AuthUnitOfWork]
