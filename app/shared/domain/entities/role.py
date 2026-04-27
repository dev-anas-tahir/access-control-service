import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.shared.domain.entities.permission import Permission


@dataclass
class Role:
    id: uuid.UUID
    name: str
    description: str | None = None
    is_system: bool = False
    created_by: uuid.UUID | None = None
    is_deleted: bool = False
    deleted_at: datetime | None = None
    created_at: datetime | None = None
    permissions: list[Permission] = field(default_factory=list)
