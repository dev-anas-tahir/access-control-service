"""Verify every RBAC event provides a complete, correct AuditContext.

These tests are the test surface for the audit integration: if to_audit_context()
is correct here, the AuditLoggingHandler needs no own tests.
"""

import uuid

from app.rbac.domain.events import (
    PermissionGranted,
    PermissionRevoked,
    RoleCreated,
    RoleDeleted,
    UserRoleAssigned,
    UserRoleRevoked,
)


def test_role_created_audit_context():
    role_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    event = RoleCreated(
        role_id=role_id,
        name="editor",
        description="can edit",
        is_system=False,
        actor_id=actor_id,
    )

    ctx = event.to_audit_context()

    assert ctx.action == "ROLE_CREATED"
    assert ctx.entity_type == "Role"
    assert ctx.entity_id == role_id
    assert ctx.payload == {
        "name": "editor",
        "description": "can edit",
        "is_system": False,
    }


def test_role_deleted_audit_context():
    role_id = uuid.uuid4()
    event = RoleDeleted(role_id=role_id, name="viewer", actor_id=uuid.uuid4())

    ctx = event.to_audit_context()

    assert ctx.action == "ROLE_DELETED"
    assert ctx.entity_type == "Role"
    assert ctx.entity_id == role_id
    assert ctx.payload == {"name": "viewer"}


def test_permission_granted_audit_context():
    role_id = uuid.uuid4()
    event = PermissionGranted(
        role_id=role_id,
        role_name="editor",
        permission_id=uuid.uuid4(),
        scope_key="catalog:write",
        actor_id=uuid.uuid4(),
    )

    ctx = event.to_audit_context()

    assert ctx.action == "PERMISSION_GRANTED"
    assert ctx.entity_type == "Role"
    assert ctx.entity_id == role_id
    assert ctx.payload == {"scope_key": "catalog:write", "role_name": "editor"}


def test_permission_revoked_audit_context():
    role_id = uuid.uuid4()
    event = PermissionRevoked(
        role_id=role_id,
        role_name="editor",
        permission_id=uuid.uuid4(),
        scope_key="catalog:write",
        actor_id=uuid.uuid4(),
    )

    ctx = event.to_audit_context()

    assert ctx.action == "PERMISSION_REVOKED"
    assert ctx.entity_type == "Role"
    assert ctx.entity_id == role_id
    assert ctx.payload == {"scope_key": "catalog:write", "role_name": "editor"}


def test_user_role_assigned_audit_context():
    user_id = uuid.uuid4()
    event = UserRoleAssigned(
        user_id=user_id,
        user_name="alice",
        role_id=uuid.uuid4(),
        role_name="editor",
        actor_id=uuid.uuid4(),
    )

    ctx = event.to_audit_context()

    assert ctx.action == "USER_ROLE_ASSIGNED"
    assert ctx.entity_type == "UserRole"
    assert ctx.entity_id == user_id
    assert ctx.payload == {"user": "alice", "role": "editor"}


def test_user_role_revoked_audit_context():
    user_id = uuid.uuid4()
    event = UserRoleRevoked(
        user_id=user_id,
        user_name="alice",
        role_id=uuid.uuid4(),
        role_name="editor",
        actor_id=uuid.uuid4(),
    )

    ctx = event.to_audit_context()

    assert ctx.action == "USER_ROLE_REVOKED"
    assert ctx.entity_type == "UserRole"
    assert ctx.entity_id == user_id
    assert ctx.payload == {"user": "alice", "role": "editor"}
