import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, kw_only=True)
class InventoryEvent:
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    actor_id: uuid.UUID | None = None

    @property
    def event_type(self) -> str:
        return self.__class__.__name__

    def to_pubsub_payload(self) -> dict:
        raise NotImplementedError


@dataclass(frozen=True, kw_only=True)
class InventoryRestocked(InventoryEvent):
    variant_id: uuid.UUID
    quantity_added: int
    quantity_on_hand: int

    def to_pubsub_payload(self) -> dict:
        return {
            "variant_id": str(self.variant_id),
            "quantity_added": self.quantity_added,
            "quantity_on_hand": self.quantity_on_hand,
        }


@dataclass(frozen=True, kw_only=True)
class InventoryDepleted(InventoryEvent):
    variant_id: uuid.UUID

    def to_pubsub_payload(self) -> dict:
        return {"variant_id": str(self.variant_id)}
