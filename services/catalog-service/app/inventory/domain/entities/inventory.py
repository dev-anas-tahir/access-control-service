import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.inventory.domain.events import InventoryDepleted, InventoryEvent


@dataclass
class Inventory:
    id: uuid.UUID
    variant_id: uuid.UUID
    quantity_on_hand: int
    quantity_reserved: int
    updated_at: datetime | None = None
    _events: list[InventoryEvent] = field(default_factory=list, repr=False)

    @property
    def available(self) -> int:
        return self.quantity_on_hand - self.quantity_reserved

    def reserve(self, qty: int) -> None:
        if qty > self.available:
            raise ValueError(f"Cannot reserve {qty}: only {self.available} available")
        self.quantity_reserved += qty

    def release(self, qty: int) -> None:
        release_qty = min(qty, self.quantity_reserved)
        self.quantity_reserved -= release_qty

    def restock(self, qty: int) -> None:
        if qty <= 0:
            raise ValueError("Restock quantity must be positive")
        self.quantity_on_hand += qty

    def commit_reservation(
        self, qty: int, *, actor_id: uuid.UUID | None = None
    ) -> None:
        commit_qty = min(qty, self.quantity_reserved)
        was_in_stock = self.quantity_on_hand > 0
        self.quantity_reserved -= commit_qty
        self.quantity_on_hand -= commit_qty
        if was_in_stock and self.quantity_on_hand == 0:
            self._events.append(
                InventoryDepleted(actor_id=actor_id, variant_id=self.variant_id)
            )

    def collect_events(self) -> list[InventoryEvent]:
        events = self._events[:]
        self._events.clear()
        return events
