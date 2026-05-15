import uuid
from datetime import datetime
from typing import Protocol

from app.shared.domain.entities.role import Role


class RoleRepository(Protocol):
    async def find_by_id(self, id: uuid.UUID) -> Role | None: ...

    async def find_by_name(self, name: str) -> Role | None: ...

    async def add(
        self,
        *,
        name: str,
        description: str | None,
        created_by: uuid.UUID,
    ) -> Role:
        """Persist a new role and return it with its DB-assigned id."""
        ...

    async def mark_deleted(self, id: uuid.UUID, when: datetime) -> None: ...
