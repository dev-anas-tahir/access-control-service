from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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
from app.shared.domain.ports.audit_logger import AuditLogger
from app.shared.infrastructure.events.audit_handler import AuditLoggingHandler


class SqlAlchemyRbacUnitOfWork:
    """SQLAlchemy-based Unit of Work for RBAC operations with domain event support.

    Accepts an audit_logger_factory so the Audit infrastructure dependency is
    injected at construction time (via composition.py) rather than hard-coded here.
    After a successful commit, pending domain events are dispatched through
    AuditLoggingHandler and persisted in a second commit, keeping audit writes
    atomic with respect to their triggering operation.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        audit_logger_factory: Callable[[AsyncSession], AuditLogger],
    ) -> None:
        self._session_factory = session_factory
        self._audit_logger_factory = audit_logger_factory
        self._events: list[DomainEvent] = []

    async def __aenter__(self) -> "SqlAlchemyRbacUnitOfWork":
        self._session = self._session_factory()
        self.roles = SqlAlchemyRoleRepository(self._session)
        self.permissions = SqlAlchemyPermissionRepository(self._session)
        self.assignments = SqlAlchemyAssignmentRepository(self._session)
        self.users = SqlAlchemyUserReader(self._session)
        self._audit_logger = self._audit_logger_factory(self._session)
        self._events = []
        return self

    async def __aexit__(self, exc_type: object, *args: object) -> None:
        if exc_type:
            await self.rollback()
            self._events.clear()
        await self._session.close()  # type: ignore[union-attr]

    async def commit(self) -> None:
        await self._session.commit()  # type: ignore[union-attr]
        events = self.collect_events()
        if events:
            handler = AuditLoggingHandler(self._audit_logger)
            await handler.handle_many(events)
            await self._session.commit()  # type: ignore[union-attr]

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
