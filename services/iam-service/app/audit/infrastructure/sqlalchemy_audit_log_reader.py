from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit.infrastructure.orm.audit_log import AuditLog as AuditLogORM
from app.shared.domain.entities.audit_log import AuditLog


def _orm_to_domain(orm: AuditLogORM) -> AuditLog:
    return AuditLog(
        id=orm.id,
        actor_id=orm.actor_id,
        action=orm.action,
        entity_type=orm.entity_type,
        entity_id=orm.entity_id,
        payload=orm.payload,
        created_at=orm.created_at,
    )


class SqlAlchemyAuditLogReader:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list_paginated(
        self, *, page: int, page_size: int
    ) -> list[AuditLog]:
        offset = (page - 1) * page_size
        async with self._session_factory() as session:
            result = await session.execute(
                select(AuditLogORM)
                .order_by(AuditLogORM.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
            return [_orm_to_domain(orm) for orm in result.scalars().all()]
