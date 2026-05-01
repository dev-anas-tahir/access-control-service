from datetime import datetime
from uuid import UUID

from app.shared.infrastructure.http.schemas import OrmSchema


class AuditLogResponse(OrmSchema):
    id: UUID
    actor_id: UUID | None
    action: str
    entity_id: UUID | None
    entity_type: str
    payload: dict | None
    created_at: datetime
