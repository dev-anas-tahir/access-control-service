from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.inventory.domain.events import InventoryEvent
from app.inventory.infrastructure.repositories.sqlalchemy_inventory_repository import (
    SqlAlchemyInventoryRepository,
)
from app.shared.infrastructure.events.pubsub_publisher import publish_event


class SqlAlchemyInventoryUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._events: list[InventoryEvent] = []

    async def __aenter__(self) -> "SqlAlchemyInventoryUnitOfWork":
        self._session = self._session_factory()
        self.inventory = SqlAlchemyInventoryRepository(self._session)
        self._events = []
        return self

    async def __aexit__(self, exc_type: object, *args: object) -> None:
        if exc_type:
            await self.rollback()
        await self._session.close()

    async def commit(self) -> None:
        await self._session.commit()
        events = self.collect_events()
        for event in events:
            await publish_event(event.event_type, event.to_pubsub_payload())

    async def rollback(self) -> None:
        await self._session.rollback()
        self._events.clear()

    def add_event(self, event: InventoryEvent) -> None:
        self._events.append(event)

    def collect_events(self) -> list[InventoryEvent]:
        events = self._events[:]
        self._events.clear()
        return events
