from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.infrastructure.repositories.sqlalchemy_role_repository import (
    SqlAlchemyRoleRepository,
)
from app.auth.infrastructure.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from app.shared.domain.events import DomainEvent


class SqlAlchemyAuthUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._events: list[DomainEvent] = []

    async def __aenter__(self) -> "SqlAlchemyAuthUnitOfWork":
        self._session = self._session_factory()
        self.users = SqlAlchemyUserRepository(self._session)
        self.roles = SqlAlchemyRoleRepository(self._session)
        self._events = []
        return self

    async def __aexit__(self, exc_type: object, *args: object) -> None:
        if exc_type:
            await self.rollback()
        await self._session.close()  # type: ignore[union-attr]

    async def commit(self) -> None:
        await self._session.commit()  # type: ignore[union-attr]

    async def rollback(self) -> None:
        await self._session.rollback()  # type: ignore[union-attr]
        self._events.clear()

    def add_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        events = self._events[:]
        self._events.clear()
        return events
