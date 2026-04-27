from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.infrastructure.sqlalchemy_audit_logger import SqlAlchemyAuditLogger
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


class SqlAlchemyRbacUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> "SqlAlchemyRbacUnitOfWork":
        self._session = self._session_factory()
        self.roles = SqlAlchemyRoleRepository(self._session)
        self.permissions = SqlAlchemyPermissionRepository(self._session)
        self.assignments = SqlAlchemyAssignmentRepository(self._session)
        self.users = SqlAlchemyUserReader(self._session)
        self.audit_logger = SqlAlchemyAuditLogger(self._session)
        return self

    async def __aexit__(self, exc_type: object, *args: object) -> None:
        if exc_type:
            await self.rollback()
        await self._session.close()  # type: ignore[union-attr]

    async def commit(self) -> None:
        await self._session.commit()  # type: ignore[union-attr]

    async def rollback(self) -> None:
        await self._session.rollback()  # type: ignore[union-attr]
