from typing import Protocol

from app.shared.domain.entities.permission import Permission


class PermissionRepository(Protocol):
    async def find_by_scope_key(self, scope_key: str) -> Permission | None: ...

    async def add(self, *, resource: str, action: str, scope_key: str) -> Permission:
        """Persist a new permission and return it with its DB-assigned id."""
        ...
