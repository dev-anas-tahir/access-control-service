from typing import Protocol

from app.shared.domain.entities.role import Role


class RoleRepository(Protocol):
    async def find_by_name(self, name: str) -> Role | None: ...
