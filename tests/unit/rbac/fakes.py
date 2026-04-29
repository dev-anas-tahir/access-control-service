"""In-memory fakes for all RBAC ports — use in unit tests."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.rbac.domain.ports.user_reader import UserSummary
from app.shared.domain.entities.permission import Permission
from app.shared.domain.entities.role import Role
from app.shared.domain.values.scope_key import ScopeKey

# ── Entity factories ──────────────────────────────────────────────────────────


def make_permission(
    resource: str = "resource", action: str = "read"
) -> Permission:
    return Permission(
        id=uuid.uuid4(),
        scope_key=ScopeKey(resource=resource, action=action),
    )


def make_role(
    name: str = "editor",
    is_system: bool = False,
    permissions: list[Permission] | None = None,
) -> Role:
    return Role(
        id=uuid.uuid4(),
        name=name,
        description=None,
        is_system=is_system,
        created_by=uuid.uuid4(),
        permissions=permissions or [],
    )


def make_user_summary(username: str = "alice") -> UserSummary:
    return UserSummary(id=uuid.uuid4(), username=username)


# ── Repository fakes ──────────────────────────────────────────────────────────


class FakeRoleRepository:
    def __init__(self, roles: list[Role] | None = None) -> None:
        self._by_id: dict[uuid.UUID, Role] = {r.id: r for r in (roles or [])}
        self._by_name: dict[str, Role] = {r.name: r for r in (roles or [])}

    async def find_by_id(self, id: uuid.UUID) -> Role | None:
        return self._by_id.get(id)

    async def find_by_name(self, name: str) -> Role | None:
        return self._by_name.get(name)

    async def add(
        self,
        *,
        name: str,
        description: str | None,
        created_by: uuid.UUID,
    ) -> Role:
        role = Role(
            id=uuid.uuid4(),
            name=name,
            description=description,
            is_system=False,
            created_by=created_by,
            created_at=datetime.now(timezone.utc),
        )
        self._by_id[role.id] = role
        self._by_name[role.name] = role
        return role

    async def mark_deleted(self, id: uuid.UUID, when: datetime) -> None:
        role = self._by_id[id]
        role.is_deleted = True
        role.deleted_at = when


class FakePermissionRepository:
    def __init__(self, permissions: list[Permission] | None = None) -> None:
        self._store: dict[str, Permission] = {
            p.scope_key.key: p for p in (permissions or [])
        }

    async def find_by_scope_key(self, scope_key: ScopeKey) -> Permission | None:
        return self._store.get(scope_key.key)

    async def add(self, scope_key: ScopeKey) -> Permission:
        perm = Permission(id=uuid.uuid4(), scope_key=scope_key)
        self._store[scope_key.key] = perm
        return perm


class FakeAssignmentRepository:
    def __init__(self) -> None:
        self._role_permissions: set[tuple[uuid.UUID, uuid.UUID]] = set()
        self._user_roles: set[tuple[uuid.UUID, uuid.UUID]] = set()

    async def role_has_permission(
        self, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> bool:
        return (role_id, permission_id) in self._role_permissions

    async def assign_permission(
        self,
        role_id: uuid.UUID,
        permission_id: uuid.UUID,
        granted_by: uuid.UUID,
    ) -> None:
        self._role_permissions.add((role_id, permission_id))

    async def revoke_permission(
        self, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> None:
        self._role_permissions.discard((role_id, permission_id))

    async def assign_role_to_user(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by: uuid.UUID,
    ) -> None:
        self._user_roles.add((user_id, role_id))

    async def revoke_role_from_user(
        self, user_id: uuid.UUID, role_id: uuid.UUID
    ) -> None:
        self._user_roles.discard((user_id, role_id))


class FakeUserReader:
    def __init__(self, users: list[UserSummary] | None = None) -> None:
        self._store: dict[uuid.UUID, UserSummary] = {
            u.id: u for u in (users or [])
        }

    async def find_summary_by_id(self, id: uuid.UUID) -> UserSummary | None:
        return self._store.get(id)


# ── Audit logger fake ─────────────────────────────────────────────────────────


@dataclass
class AuditEntry:
    actor_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID | None
    payload: dict[str, Any] | None


class FakeAuditLogger:
    def __init__(self) -> None:
        self.entries: list[AuditEntry] = []

    async def log(
        self,
        *,
        actor_id: uuid.UUID | None,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.entries.append(
            AuditEntry(
                actor_id=actor_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                payload=payload,
            )
        )


# ── Unit of Work fake ─────────────────────────────────────────────────────────


class FakeRbacUnitOfWork:
    def __init__(
        self,
        roles: FakeRoleRepository | None = None,
        permissions: FakePermissionRepository | None = None,
        assignments: FakeAssignmentRepository | None = None,
        users: FakeUserReader | None = None,
        audit_logger: FakeAuditLogger | None = None,
    ) -> None:
        self.roles = roles or FakeRoleRepository()
        self.permissions = permissions or FakePermissionRepository()
        self.assignments = assignments or FakeAssignmentRepository()
        self.users = users or FakeUserReader()
        self.audit_logger = audit_logger or FakeAuditLogger()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> "FakeRbacUnitOfWork":
        return self

    async def __aexit__(self, exc_type: object, *args: object) -> None:
        if exc_type:
            self.rolled_back = True

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True
