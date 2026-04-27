import uuid
from typing import Protocol


class AssignmentRepository(Protocol):
    """Manages many-to-many assignments: role↔permission and user↔role."""

    # ── Role ↔ Permission ────────────────────────────────────────────────────
    async def role_has_permission(
        self, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> bool: ...

    async def assign_permission(
        self,
        role_id: uuid.UUID,
        permission_id: uuid.UUID,
        granted_by: uuid.UUID,
    ) -> None: ...

    async def revoke_permission(
        self, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> None: ...

    # ── User ↔ Role ──────────────────────────────────────────────────────────
    async def assign_role_to_user(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by: uuid.UUID,
    ) -> None: ...

    async def revoke_role_from_user(
        self, user_id: uuid.UUID, role_id: uuid.UUID
    ) -> None: ...
