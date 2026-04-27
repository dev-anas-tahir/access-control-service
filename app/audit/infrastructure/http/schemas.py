from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_id: UUID | None
    action: str
    entity_id: UUID | None
    entity_type: str
    payload: dict | None
    created_at: datetime
