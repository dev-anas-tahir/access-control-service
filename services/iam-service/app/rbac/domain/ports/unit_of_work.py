from typing import Callable, Protocol

from app.rbac.domain.ports.assignment_repository import AssignmentRepository
from app.rbac.domain.ports.permission_repository import PermissionRepository
from app.rbac.domain.ports.role_repository import RoleRepository
from app.rbac.domain.ports.user_reader import UserReader
from app.shared.domain.events import DomainEvent
from app.shared.domain.ports.audit_logger import AuditLogger


class RbacUnitOfWork(Protocol):
    roles: RoleRepository
    permissions: PermissionRepository
    assignments: AssignmentRepository
    users: UserReader
    audit_logger: AuditLogger

    async def __aenter__(self) -> "RbacUnitOfWork": ...

    async def __aexit__(self, *args: object) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    def add_event(self, event: DomainEvent) -> None:
        """Add a domain event to be dispatched after commit."""
        ...

    def collect_events(self) -> list[DomainEvent]:
        """Collect all pending domain events and clear the queue."""
        ...


RbacUnitOfWorkFactory = Callable[[], RbacUnitOfWork]
