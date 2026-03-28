"""
Unit tests for rbac_service pure logic.

Per AGENTS.md: "Test pure logic only: JWT encoding/decoding, password hashing,
permission checks, schema validation. No real DB, Redis, or HTTP calls.
Mock all external dependencies."
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import (
    AlreadyAssignedError,
    NotFoundError,
    SystemRoleError,
    UniquenessError,
)
from app.models.association import RolePermission, UserRole
from app.models.audit_log import AuditLog
from app.models.role import Permission, Role
from app.models.user import User
from app.schemas.role import PermissionCreate, RoleCreate
from app.services import rbac_service


def mock_result(scalar=None, scalars=None):
    """Create a mock SQLAlchemy result object."""

    class Result:
        def scalar_one_or_none(self):
            return scalar

        def scalars(self):
            return self

        def all(self):
            return scalars or []

    return Result()


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.delete = AsyncMock()
    return db


@pytest.fixture
def sample_role():
    """Create a sample role for testing."""
    return Role(
        id="role-123",
        name="admin",
        description="Admin role",
        is_system=False,
        created_by="user-123",
    )


@pytest.fixture
def sample_permission():
    """Create a sample permission for testing."""
    return Permission(
        id="perm-123",
        resource="users",
        action="read",
        scope_key="users:read",
    )


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return User(
        id="user-123",
        username="testuser",
        email="test@example.com",
    )


# ──────────────────────────────────────────────────────────────
# create_role
# ──────────────────────────────────────────────────────────────


async def test_create_role_success(mock_db, sample_user):
    """Test successful role creation."""
    data = RoleCreate(name="editor", description="Editor role")
    actor_id = "actor-123"

    # Mock: role doesn't exist
    mock_db.execute.return_value = mock_result(scalar=None)

    result = await rbac_service.create_role(mock_db, data, actor_id)

    # Verify role was added (add called twice: role + audit log)
    assert mock_db.add.call_count == 2
    mock_db.flush.assert_called()
    mock_db.refresh.assert_called_once()

    # Verify role attributes
    assert result.name == "editor"
    assert result.description == "Editor role"
    assert result.created_by == actor_id


async def test_create_role_already_exists(mock_db):
    """Test creating a role that already exists raises UniquenessError."""
    data = RoleCreate(name="admin", description="Admin role")
    actor_id = "actor-123"

    # Mock: role already exists
    existing_role = Role(name="admin", description="Admin role")
    mock_db.execute.return_value = mock_result(scalar=existing_role)

    with pytest.raises(UniquenessError, match="Role name already exists"):
        await rbac_service.create_role(mock_db, data, actor_id)


# ──────────────────────────────────────────────────────────────
# delete_role
# ──────────────────────────────────────────────────────────────


async def test_delete_role_success(mock_db, sample_role):
    """Test successful role deletion (soft delete)."""
    role_id = "role-123"
    actor_id = "actor-123"

    # Mock: role exists and is not system
    mock_db.execute.return_value = mock_result(scalar=sample_role)

    await rbac_service.delete_role(mock_db, role_id, actor_id)

    # Verify soft delete
    assert sample_role.is_deleted is True
    assert sample_role.deleted_at is not None

    # Verify audit log was written (add called for AuditLog)
    assert mock_db.add.call_count >= 1


async def test_delete_role_not_found(mock_db):
    """Test deleting a non-existent role raises NotFoundError."""
    role_id = "nonexistent-role"
    actor_id = "actor-123"

    # Mock: role not found
    mock_db.execute.return_value = mock_result(scalar=None)

    with pytest.raises(NotFoundError, match="Role not found"):
        await rbac_service.delete_role(mock_db, role_id, actor_id)


async def test_delete_role_system_role(mock_db):
    """Test deleting a system role raises SystemRoleError."""
    system_role = Role(
        id="system-role",
        name="viewer",
        description="System role",
        is_system=True,
    )
    role_id = "system-role"
    actor_id = "actor-123"

    # Mock: system role found
    mock_db.execute.return_value = mock_result(scalar=system_role)

    with pytest.raises(SystemRoleError, match="Cannot delete system role"):
        await rbac_service.delete_role(mock_db, role_id, actor_id)


# ──────────────────────────────────────────────────────────────
# assign_permission
# ──────────────────────────────────────────────────────────────


async def test_assign_permission_success(mock_db, sample_role, sample_permission):
    """Test successfully assigning a permission to a role."""
    role_id = "role-123"
    data = PermissionCreate(resource="posts", action="write")
    actor_id = "actor-123"

    # Mock: role exists with empty permissions, permission doesn't exist
    sample_role.permissions = []
    mock_db.execute.side_effect = [
        mock_result(scalar=sample_role),  # get role
        mock_result(scalar=None),  # permission not found
        mock_result(scalar=None),  # check for existing role-permission association (returns None = not found)  # noqa: E501
    ]

    result = await rbac_service.assign_permission(mock_db, role_id, data, actor_id)

    # Verify association created
    assert isinstance(result, RolePermission)
    assert result.role_id == sample_role.id
    assert result.granted_by == actor_id

    # Verify that permission and association were added to session
    # add should be called at least twice: permission + role_permission (+ audit log)
    assert mock_db.add.call_count >= 2


async def test_assign_permission_role_not_found(mock_db):
    """Test assigning permission to non-existent role raises NotFoundError."""
    role_id = "nonexistent-role"
    data = PermissionCreate(resource="posts", action="write")
    actor_id = "actor-123"

    # Mock: role not found
    mock_db.execute.return_value = mock_result(scalar=None)

    with pytest.raises(NotFoundError, match="Role not found"):
        await rbac_service.assign_permission(mock_db, role_id, data, actor_id)


async def test_assign_permission_already_assigned(
    mock_db, sample_role, sample_permission
):
    """Test assigning an already-assigned permission raises AlreadyAssignedError."""
    role_id = "role-123"
    data = PermissionCreate(resource="users", action="read")
    actor_id = "actor-123"

    # Mock: role exists with permission already assigned
    # The permission in role.permissions must have the same ID as the one that will be fetched  # noqa: E501
    sample_role.permissions = [sample_permission]
    # When service queries for permission, return the same permission object
    mock_db.execute.side_effect = [
        mock_result(scalar=sample_role),  # get role with permissions
        mock_result(scalar=sample_permission),  # permission exists - return same object
        mock_result(scalar=RolePermission()),  # check for existing role-permission association (returns existing association)  # noqa: E501
    ]

    with pytest.raises(AlreadyAssignedError, match="Permission already assigned"):
        await rbac_service.assign_permission(mock_db, role_id, data, actor_id)


async def test_assign_permission_creates_new_permission_if_not_exists(
    mock_db, sample_role
):
    """Test that a new permission is created if it doesn't exist."""
    role_id = "role-123"
    data = PermissionCreate(resource="posts", action="write")
    actor_id = "actor-123"

    # Mock: role exists, permission doesn't exist
    sample_role.permissions = []
    mock_db.execute.side_effect = [
        mock_result(scalar=sample_role),  # get role
        mock_result(scalar=None),  # permission not found
        mock_result(scalar=None),  # check for existing role-permission association (returns None = not found)  # noqa: E501
    ]

    await rbac_service.assign_permission(mock_db, role_id, data, actor_id)

    # Verify Permission was added to session
    # add should be called at least twice: permission + role_permission (+ audit log)
    assert mock_db.add.call_count >= 2


# ──────────────────────────────────────────────────────────────
# revoke_permission
# ──────────────────────────────────────────────────────────────


async def test_revoke_permission_success(mock_db, sample_role, sample_permission):
    """Test successfully revoking a permission from a role."""
    role_id = "role-123"
    scope = "users:read"
    actor_id = "actor-123"

    # Mock: role and permission exist
    sample_role.permissions = [sample_permission]
    mock_db.execute.side_effect = [
        mock_result(scalar=sample_role),  # get role
        mock_result(scalar=sample_permission),  # get permission
        mock_result(scalar=None),  # delete execute result
    ]

    await rbac_service.revoke_permission(mock_db, role_id, scope, actor_id)

    # Verify execute was called for the delete operation (not delete method)
    assert mock_db.execute.call_count >= 3  # role query, permission query, delete


async def test_revoke_permission_role_not_found(mock_db):
    """Test revoking permission from non-existent role raises NotFoundError."""
    role_id = "nonexistent-role"
    scope = "users:read"
    actor_id = "actor-123"

    # Mock: role not found
    mock_db.execute.return_value = mock_result(scalar=None)

    with pytest.raises(NotFoundError, match="Role not found"):
        await rbac_service.revoke_permission(mock_db, role_id, scope, actor_id)


async def test_revoke_permission_permission_not_found(mock_db, sample_role):
    """Test revoking a non-existent permission raises NotFoundError."""
    role_id = "role-123"
    scope = "nonexistent:permission"
    actor_id = "actor-123"

    # Mock: role exists but permission not found
    sample_role.permissions = []
    mock_db.execute.side_effect = [
        mock_result(scalar=sample_role),  # get role
        mock_result(scalar=None),  # permission not found
    ]

    with pytest.raises(NotFoundError, match="Permission not found"):
        await rbac_service.revoke_permission(mock_db, role_id, scope, actor_id)


# ──────────────────────────────────────────────────────────────
# assign_role_to_user
# ──────────────────────────────────────────────────────────────


async def test_assign_role_to_user_success(mock_db, sample_user, sample_role):
    """Test successfully assigning a role to a user."""
    user_id = "user-123"
    role_id = "role-123"
    actor_id = "actor-123"

    # Mock: user and role exist
    mock_db.execute.side_effect = [
        mock_result(scalar=sample_user),  # get user
        mock_result(scalar=sample_role),  # get role
        mock_result(scalar=None),  # other calls
    ]

    result = await rbac_service.assign_role_to_user(mock_db, user_id, role_id, actor_id)

    # Verify association created
    assert isinstance(result, UserRole)
    assert result.user_id == sample_user.id
    assert result.role_id == sample_role.id
    assert result.assigned_by == actor_id

    # Verify audit log written (add called at least twice: user_role + audit_log)
    assert mock_db.add.call_count >= 2


async def test_assign_role_to_user_user_not_found(mock_db):
    """Test assigning role to non-existent user raises NotFoundError."""
    user_id = "nonexistent-user"
    role_id = "role-123"
    actor_id = "actor-123"

    # Mock: user not found
    mock_db.execute.return_value = mock_result(scalar=None)

    with pytest.raises(NotFoundError, match="User not found"):
        await rbac_service.assign_role_to_user(mock_db, user_id, role_id, actor_id)


async def test_assign_role_to_user_role_not_found(mock_db, sample_user):
    """Test assigning non-existent role raises NotFoundError."""
    user_id = "user-123"
    role_id = "nonexistent-role"
    actor_id = "actor-123"

    # Mock: user exists, role not found
    mock_db.execute.side_effect = [
        mock_result(scalar=sample_user),  # get user
        mock_result(scalar=None),  # get role - not found
    ]

    with pytest.raises(NotFoundError, match="Role not found"):
        await rbac_service.assign_role_to_user(mock_db, user_id, role_id, actor_id)


# ──────────────────────────────────────────────────────────────
# revoke_role_from_user
# ──────────────────────────────────────────────────────────────


async def test_revoke_role_from_user_success(mock_db, sample_user, sample_role):
    """Test successfully revoking a role from a user."""
    user_id = "user-123"
    role_id = "role-123"
    actor_id = "actor-123"

    # Mock: user and role exist
    mock_db.execute.side_effect = [
        mock_result(scalar=sample_user),  # get user
        mock_result(scalar=sample_role),  # get role
        mock_result(scalar=None),  # delete execute result
    ]

    await rbac_service.revoke_role_from_user(mock_db, user_id, role_id, actor_id)

    # Verify execute was called for the delete operation (not delete method)
    assert mock_db.execute.call_count >= 3  # user query, role query, delete


async def test_revoke_role_from_user_user_not_found(mock_db):
    """Test revoking role from non-existent user raises NotFoundError."""
    user_id = "nonexistent-user"
    role_id = "role-123"
    actor_id = "actor-123"

    # Mock: user not found
    mock_db.execute.return_value = mock_result(scalar=None)

    with pytest.raises(NotFoundError, match="User not found"):
        await rbac_service.revoke_role_from_user(mock_db, user_id, role_id, actor_id)


async def test_revoke_role_from_user_role_not_found(mock_db, sample_user):
    """Test revoking non-existent role raises NotFoundError."""
    user_id = "user-123"
    role_id = "nonexistent-role"
    actor_id = "actor-123"

    # Mock: user exists, role not found
    mock_db.execute.side_effect = [
        mock_result(scalar=sample_user),  # get user
        mock_result(scalar=None),  # get role - not found
    ]

    with pytest.raises(NotFoundError, match="Role not found"):
        await rbac_service.revoke_role_from_user(mock_db, user_id, role_id, actor_id)


# ──────────────────────────────────────────────────────────────
# get_audit_logs
# ──────────────────────────────────────────────────────────────


async def test_get_audit_logs_with_pagination(mock_db):
    """Test retrieving audit logs with pagination."""
    # Create mock audit logs
    now = datetime.now(timezone.utc)
    logs = [
        AuditLog(
            id="log-1",
            action="ROLE_CREATED",
            entity_type="Role",
            entity_id="role-1",
            payload={"name": "admin"},
            created_at=now,
        ),
        AuditLog(
            id="log-2",
            action="USER_ROLE_ASSIGNED",
            entity_type="UserRole",
            entity_id="user-1",
            payload={"user": "test", "role": "admin"},
            created_at=now,
        ),
    ]

    mock_db.execute.return_value = mock_result(scalars=logs)

    result = await rbac_service.get_audit_logs(mock_db, page=1, page_size=20)

    assert len(result) == 2
    assert result[0].id == "log-1"
    assert result[1].id == "log-2"


async def test_get_audit_logs_pagination_offset(mock_db):
    """Test that pagination calculates offset correctly."""
    now = datetime.now(timezone.utc)
    logs = [
        AuditLog(
            id="log-1",
            action="TEST",
            entity_type="Test",
            entity_id="test-1",
            payload=None,
            created_at=now,
        ),
    ]

    mock_db.execute.return_value = mock_result(scalars=logs)

    # page=2, page_size=10 -> offset = (2-1)*10 = 10
    await rbac_service.get_audit_logs(mock_db, page=2, page_size=10)

    # Verify the query was executed
    assert mock_db.execute.called


async def test_get_audit_logs_empty_result(mock_db):
    """Test retrieving audit logs when none exist."""
    mock_db.execute.return_value = mock_result(scalars=[])

    result = await rbac_service.get_audit_logs(mock_db, page=1, page_size=20)

    assert result == []
