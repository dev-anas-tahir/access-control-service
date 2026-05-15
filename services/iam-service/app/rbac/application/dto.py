import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class CreateRoleInput:
    name: str
    description: str | None
    actor_id: uuid.UUID


@dataclass
class CreateRoleResult:
    id: uuid.UUID
    name: str
    description: str | None
    is_system: bool
    created_by: uuid.UUID | None
    created_at: datetime | None


@dataclass
class DeleteRoleInput:
    role_id: uuid.UUID
    actor_id: uuid.UUID


@dataclass
class AssignPermissionInput:
    role_id: uuid.UUID
    resource: str
    action: str
    actor_id: uuid.UUID


@dataclass
class AssignPermissionResult:
    role_id: uuid.UUID
    permission_id: uuid.UUID


@dataclass
class RevokePermissionInput:
    role_id: uuid.UUID
    scope_key: str
    actor_id: uuid.UUID


@dataclass
class AssignRoleToUserInput:
    user_id: uuid.UUID
    role_id: uuid.UUID
    actor_id: uuid.UUID


@dataclass
class AssignRoleToUserResult:
    user_id: uuid.UUID
    role_id: uuid.UUID


@dataclass
class RevokeRoleFromUserInput:
    user_id: uuid.UUID
    role_id: uuid.UUID
    actor_id: uuid.UUID
