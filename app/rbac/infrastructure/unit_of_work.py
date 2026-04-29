from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.infrastructure.sqlalchemy_audit_logger import SqlAlchemyAuditLogger
from app.rbac.domain.events import (
    PermissionGranted,
    PermissionRevoked,
    RoleCreated,
    RoleDeleted,
    UserRoleAssigned,
    UserRoleRevoked,
)
from app.rbac.infrastructure.repositories.sqlalchemy_assignment_repository import (
    SqlAlchemyAssignmentRepository,
)
from app.rbac.infrastructure.repositories.sqlalchemy_permission_repository import (
    SqlAlchemyPermissionRepository,
)
from app.rbac.infrastructure.repositories.sqlalchemy_role_repository import (
    SqlAlchemyRoleRepository,
)
from app.rbac.infrastructure.repositories.sqlalchemy_user_reader import (
    SqlAlchemyUserReader,
)
from app.shared.domain.events import DomainEvent


class SqlAlchemyRbacUnitOfWork:
    """SQLAlchemy-based Unit of Work for RBAC operations with domain event support.

    This UoW collects domain events during operations and dispatches them
    to audit logging after successful commit, decoupling RBAC use cases
    from the Audit context.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._events: list[DomainEvent] = []

    async def __aenter__(self) -> "SqlAlchemyRbacUnitOfWork":
        self._session = self._session_factory()
        self.roles = SqlAlchemyRoleRepository(self._session)
        self.permissions = SqlAlchemyPermissionRepository(self._session)
        self.assignments = SqlAlchemyAssignmentRepository(self._session)
        self.users = SqlAlchemyUserReader(self._session)
        self.audit_logger = SqlAlchemyAuditLogger(self._session)
        self._events = []  # Reset events on entry
        return self

    async def __aexit__(self, exc_type: object, *args: object) -> None:
        if exc_type:
            await self.rollback()
            self._events.clear()  # Clear events on rollback
        await self._session.close()  # type: ignore[union-attr]

    async def commit(self) -> None:
        await self._session.commit()  # type: ignore[union-attr]
        # Dispatch events after successful commit
        await self._process_events()

    async def rollback(self) -> None:
        await self._session.rollback()  # type: ignore[union-attr]
        self._events.clear()

    def add_event(self, event: DomainEvent) -> None:
        """Add a domain event to be dispatched after commit."""
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        """Collect all pending domain events and clear the queue."""
        events = self._events[:]
        self._events.clear()
        return events

    async def _process_events(self) -> None:
        """Process collected events by creating audit log entries.

        This method maps domain events to audit log entries, decoupling
        the RBAC context from the Audit context via domain events.
        """
        if not self._events:
            return

        events = self.collect_events()
        for event in events:
            await self._handle_event(event)

    async def _handle_event(self, event: DomainEvent) -> None:
        """Map a domain event to an audit log entry.

        Args:
            event: The domain event to handle
        """
        if isinstance(event, RoleCreated):
            await self.audit_logger.log(
                actor_id=event.actor_id,
                action="ROLE_CREATED",
                entity_type="Role",
                entity_id=event.role_id,
                payload=event.to_audit_payload(),
            )
        elif isinstance(event, RoleDeleted):
            await self.audit_logger.log(
                actor_id=event.actor_id,
                action="ROLE_DELETED",
                entity_type="Role",
                entity_id=event.role_id,
                payload=event.to_audit_payload(),
            )
        elif isinstance(event, PermissionGranted):
            await self.audit_logger.log(
                actor_id=event.actor_id,
                action="PERMISSION_GRANTED",
                entity_type="Role",
                entity_id=event.role_id,
                payload=event.to_audit_payload(),
            )
        elif isinstance(event, PermissionRevoked):
            await self.audit_logger.log(
                actor_id=event.actor_id,
                action="PERMISSION_REVOKED",
                entity_type="Role",
                entity_id=event.role_id,
                payload=event.to_audit_payload(),
            )
        elif isinstance(event, UserRoleAssigned):
            await self.audit_logger.log(
                actor_id=event.actor_id,
                action="USER_ROLE_ASSIGNED",
                entity_type="UserRole",
                entity_id=event.user_id,
                payload=event.to_audit_payload(),
            )
        elif isinstance(event, UserRoleRevoked):
            await self.audit_logger.log(
                actor_id=event.actor_id,
                action="USER_ROLE_REVOKED",
                entity_type="UserRole",
                entity_id=event.user_id,
                payload=event.to_audit_payload(),
            )
