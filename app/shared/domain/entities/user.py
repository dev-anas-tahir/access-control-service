import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.shared.domain.entities.role import Role


@dataclass
class User:
    id: uuid.UUID
    username: str
    password_hash: str
    is_active: bool
    is_super_user: bool
    roles: list[Role] = field(default_factory=list)
    email: str | None = None
    organization_id: uuid.UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
