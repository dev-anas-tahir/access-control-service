from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.shared.infrastructure.http.schemas import OrmSchema


class RoleCreate(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    description: str | None = None


class RoleResponse(OrmSchema):
    id: UUID
    name: str
    description: str | None = None
    is_system: bool
    created_by: UUID | None = None
    created_at: datetime


class PermissionCreate(BaseModel):
    resource: str = Field(min_length=1, max_length=100)
    action: str = Field(min_length=1, max_length=100)


class AssignRoleRequest(BaseModel):
    role_id: UUID


class RolePermissionResponse(BaseModel):
    role_id: UUID
    permission_id: UUID


class UserRoleResponse(BaseModel):
    user_id: UUID
    role_id: UUID
