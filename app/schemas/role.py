"""Schemas for role and permission management."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RoleCreate(BaseModel):
    """Request schema for creating a new role."""

    name: str = Field(min_length=3, max_length=100)
    description: str | None = None


class RoleResponse(BaseModel):
    """Response schema for role information."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    is_system: bool
    created_by: UUID | None = None
    created_at: datetime


class PermissionCreate(BaseModel):
    """Request schema for creating a new permission."""

    resource: str = Field(min_length=1, max_length=100)
    action: str = Field(min_length=1, max_length=100)


class PermissionResponse(BaseModel):
    """Response schema for permission information."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resource: str
    action: str
    scope_key: str
    created_at: datetime


class AssignRoleRequest(BaseModel):
    """Request schema for assigning a role to a user."""

    role_id: UUID


class AuditLogResponse(BaseModel):
    """Response schema for audit log entries."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_id: UUID | None
    action: str
    entity_id: UUID | None
    entity_type: str
    payload: dict | None
    created_at: datetime


class RolePermissionResponse(BaseModel):
    """Response schema for role-permission assignment."""

    model_config = ConfigDict(from_attributes=True)

    role_id: UUID
    permission_id: UUID
    granted_by: UUID | None
    granted_at: datetime


class UserRoleResponse(BaseModel):
    """Response schema for user-role assignment."""

    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    role_id: UUID
    assigned_by: UUID | None
    assigned_at: datetime
