import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class InventoryResponse(BaseModel):
    id: uuid.UUID
    variant_id: uuid.UUID
    quantity_on_hand: int
    quantity_reserved: int
    available: int
    updated_at: datetime | None


class RestockRequest(BaseModel):
    quantity: int = Field(gt=0)


class ReserveRequest(BaseModel):
    quantity: int = Field(gt=0)


class ReleaseRequest(BaseModel):
    quantity: int = Field(gt=0)
