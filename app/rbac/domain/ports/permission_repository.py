from typing import Protocol

from app.shared.domain.entities.permission import Permission
from app.shared.domain.values.scope_key import ScopeKey


class PermissionRepository(Protocol):
    async def find_by_scope_key(self, scope_key: ScopeKey) -> Permission | None: ...

    async def add(self, scope_key: ScopeKey) -> Permission:
        """Persist a new permission and return it with its DB-assigned id."""
        ...
