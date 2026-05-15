import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.shared.domain.entities.role import Role
from app.shared.domain.values.email import Email


@dataclass
class User:
    id: uuid.UUID
    username: str
    password_hash: str
    is_active: bool
    is_super_user: bool
    roles: list[Role] = field(default_factory=list)
    email: Email | None = None
    organization_id: uuid.UUID | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def is_authenticatable(self) -> bool:
        """Whether this user is allowed to authenticate (login or refresh).

        Returned as a query rather than an assert so the use case can map
        any failure to InvalidCredentialsError without leaking *why* the
        user was rejected (existence, inactive, etc.).
        """
        return self.is_active
