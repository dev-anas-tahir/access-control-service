"""In-memory fakes for inventory ports — use in unit tests."""

import uuid
from datetime import datetime, timezone

from app.inventory.domain.entities.inventory import Inventory
from app.inventory.domain.events import InventoryEvent


def make_inventory(
    variant_id: uuid.UUID | None = None,
    on_hand: int = 10,
    reserved: int = 0,
) -> Inventory:
    return Inventory(
        id=uuid.uuid4(),
        variant_id=variant_id or uuid.uuid4(),
        quantity_on_hand=on_hand,
        quantity_reserved=reserved,
        updated_at=datetime.now(timezone.utc),
    )


class FakeInventoryRepository:
    def __init__(self, records: list[Inventory] | None = None) -> None:
        self._store: dict[uuid.UUID, Inventory] = {
            inv.variant_id: inv for inv in (records or [])
        }

    async def find_by_variant_id(self, variant_id: uuid.UUID) -> Inventory | None:
        return self._store.get(variant_id)

    async def add(self, *, variant_id: uuid.UUID) -> Inventory:
        inv = make_inventory(variant_id=variant_id, on_hand=0, reserved=0)
        self._store[variant_id] = inv
        return inv

    async def save(self, inventory: Inventory) -> None:
        self._store[inventory.variant_id] = inventory


class FakeInventoryUnitOfWork:
    def __init__(self, inventory: FakeInventoryRepository | None = None) -> None:
        self.inventory = inventory or FakeInventoryRepository()
        self.committed = False
        self._events: list[InventoryEvent] = []
        self.emitted_events: list[InventoryEvent] = []

    async def __aenter__(self) -> "FakeInventoryUnitOfWork":
        self._events = []
        return self

    async def __aexit__(self, exc_type: object, *args: object) -> None:
        if exc_type:
            self._events.clear()

    async def commit(self) -> None:
        self.committed = True
        self.emitted_events.extend(self._events)
        self._events.clear()

    async def rollback(self) -> None:
        self._events.clear()

    def add_event(self, event: InventoryEvent) -> None:
        self._events.append(event)

    def collect_events(self) -> list[InventoryEvent]:
        events = self._events[:]
        self._events.clear()
        return events
