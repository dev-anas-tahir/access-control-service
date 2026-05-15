from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.catalog.domain.events import CatalogEvent
from app.catalog.infrastructure.repositories.sqlalchemy_category_repository import (
    SqlAlchemyCategoryRepository,
)
from app.catalog.infrastructure.repositories.sqlalchemy_product_repository import (
    SqlAlchemyProductRepository,
)
from app.shared.infrastructure.events.pubsub_publisher import publish_event


class SqlAlchemyCatalogUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._events: list[CatalogEvent] = []

    async def __aenter__(self) -> "SqlAlchemyCatalogUnitOfWork":
        self._session = self._session_factory()
        self.products = SqlAlchemyProductRepository(self._session)
        self.categories = SqlAlchemyCategoryRepository(self._session)
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

    def add_event(self, event: CatalogEvent) -> None:
        self._events.append(event)

    def collect_events(self) -> list[CatalogEvent]:
        events = self._events[:]
        self._events.clear()
        return events
