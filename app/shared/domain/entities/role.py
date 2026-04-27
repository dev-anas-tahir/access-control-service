import uuid
from dataclasses import dataclass, field

from app.shared.domain.entities.permission import Permission


@dataclass
class Role:
    id: uuid.UUID
    name: str
    permissions: list[Permission] = field(default_factory=list)
