import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.infrastructure.orm.audit_log import AuditLog as AuditLogORM


class SqlAlchemyAuditLogger:
    """Implements the AuditLogger port. Joins the caller's session — no commit."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def log(
        self,
        actor_id: uuid.UUID,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID,
        payload: dict[str, Any] | None = None,
    ) -> None:
        orm = AuditLogORM(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload,
        )
        self._session.add(orm)
