import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, kw_only=True)
class CatalogEvent:
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    actor_id: uuid.UUID | None = None

    @property
    def event_type(self) -> str:
        return self.__class__.__name__

    def to_pubsub_payload(self) -> dict:
        raise NotImplementedError


@dataclass(frozen=True, kw_only=True)
class ProductPublished(CatalogEvent):
    product_id: uuid.UUID
    name: str
    category_id: uuid.UUID

    def to_pubsub_payload(self) -> dict:
        return {
            "product_id": str(self.product_id),
            "name": self.name,
            "category_id": str(self.category_id),
        }


@dataclass(frozen=True, kw_only=True)
class ProductPriceChanged(CatalogEvent):
    product_id: uuid.UUID
    variant_id: uuid.UUID
    sku: str
    old_price: float
    new_price: float

    def to_pubsub_payload(self) -> dict:
        return {
            "product_id": str(self.product_id),
            "variant_id": str(self.variant_id),
            "sku": self.sku,
            "old_price": self.old_price,
            "new_price": self.new_price,
        }
