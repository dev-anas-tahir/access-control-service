import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class AuditLog:
    id: uuid.UUID
    actor_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    payload: dict[str, Any] | None = None
    created_at: datetime | None = None
