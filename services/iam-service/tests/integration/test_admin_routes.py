"""
Integration tests for admin API routes.

Tests all admin endpoints with real database operations (but mocked external services).
"""

from httpx import AsyncClient, Response

from app.audit.infrastructure.orm.audit_log import AuditLog
from app.rbac.infrastructure.orm.association import RolePermission, UserRole
from app.rbac.infrastructure.orm.role import Permission, Role


async def test_create_role_success(client: AsyncClient, admin_token, viewer_role):
    """Test creating a new role successfully."""
    payload = {
        "name": "editor",
        "description": "Can edit content",
    }

    response: Response = await client.post(
        "/api/v1/admin/roles",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "editor"
    assert data["description"] == "Can edit content"
    assert data["is_system"] is False
    assert "id" in data
    assert "created_at" in data


async def test_create_role_duplicate_name(
    client: AsyncClient, admin_token, viewer_role
):
    """Test creating a role with a duplicate name returns 409."""
    payload = {
        "name": "viewer",  # viewer role already exists from fixture
        "description": "Duplicate role",
    }

    response: Response = await client.post(
        "/api/v1/admin/roles",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 409
    data = response.json()
    assert "already exists" in data["detail"]


async def test_delete_role_success(client: AsyncClient, admin_token, db, admin_user):
    """Test deleting a role successfully."""
    # Create a new role to delete (not a system role)

    from app.rbac.infrastructure.orm.role import Role

    new_role = Role(
        name="test_deletable_role",
        description="A role for testing deletion",
        is_system=False,
        created_by=admin_user.id,  # Use existing user ID
    )
    db.add(new_role)
    await db.commit()
    await db.refresh(new_role)

    role_id = str(new_role.id)

    response: Response = await client.delete(
        f"/api/v1/admin/roles/{role_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 204

    # Expire the identity-map entry so the next load hits the DB fresh
    # (the UoW committed in a separate session — our session cache is stale)
    await db.refresh(new_role)
    assert new_role.is_deleted is True


async def test_delete_system_role_forbidden(
    client: AsyncClient, admin_token, viewer_role
):
    """Test deleting a system role returns 403."""
    # viewer_role is a system role (is_system=True)
    role_id = str(viewer_role.id)

    response: Response = await client.delete(
        f"/api/v1/admin/roles/{role_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 403
    data = response.json()
    assert "Cannot delete system role" in data["detail"]


async def test_delete_role_not_found(client: AsyncClient, admin_token):
    """Test deleting a non-existent role returns 404."""
    non_existent_id = "00000000-0000-0000-0000-000000000000"

    response: Response = await client.delete(
        f"/api/v1/admin/roles/{non_existent_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404
    data = response.json()
    assert "Role not found" in data["detail"]


async def test_assign_permission_success(
    client: AsyncClient, admin_token, viewer_role, db
):
    """Test assigning a permission to a role successfully."""
    permission_data = {
        "resource": "posts",
        "action": "create",
    }

    response: Response = await client.post(
        f"/api/v1/admin/roles/{viewer_role.id}/permissions",
        json=permission_data,
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 201

    # Verify permission was assigned - need to commit transaction first
    await db.commit()

    # Verify permission was assigned
    from sqlalchemy import select

    result = await db.execute(
        select(RolePermission)
        .where(RolePermission.role_id == viewer_role.id)
        .join(Permission, RolePermission.permission_id == Permission.id)
        .where(Permission.scope_key == "posts:create")
    )
    association = result.scalar_one_or_none()
    assert association is not None


async def test_assign_permission_role_not_found(client: AsyncClient, admin_token):
    """Test assigning permission to non-existent role returns 404."""
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    permission_data = {
        "resource": "posts",
        "action": "create",
    }

    response: Response = await client.post(
        f"/api/v1/admin/roles/{non_existent_id}/permissions",
        json=permission_data,
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404
    data = response.json()
    assert "Role not found" in data["detail"]


async def test_assign_permission_already_assigned(
    client: AsyncClient, admin_token, viewer_role, db
):
    """Test assigning an already-assigned permission returns 409."""
    # First, assign a permission
    permission_data = {
        "resource": "users",
        "action": "read",
    }

    response1 = await client.post(
        f"/api/v1/admin/roles/{viewer_role.id}/permissions",
        json=permission_data,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response1.status_code == 201  # First assignment should succeed

    # Try to assign the same permission again - this should fail
    response: Response = await client.post(
        f"/api/v1/admin/roles/{viewer_role.id}/permissions",
        json=permission_data,
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 409
    data = response.json()
    assert "Permission already assigned" in data["detail"]


async def test_revoke_permission_success(
    client: AsyncClient, admin_token, viewer_role, db
):
    """Test revoking a permission from a role successfully."""
    # First, assign a permission
    permission_data = {
        "resource": "posts",
        "action": "delete",
    }

    await client.post(
        f"/api/v1/admin/roles/{viewer_role.id}/permissions",
        json=permission_data,
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    # Now revoke it
    scope = "posts:delete"
    response: Response = await client.delete(
        f"/api/v1/admin/roles/{viewer_role.id}/permissions/{scope}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 204

    # Verify permission was revoked
    from sqlalchemy import select

    result = await db.execute(
        select(RolePermission)
        .where(RolePermission.role_id == viewer_role.id)
        .join(Permission, RolePermission.permission_id == Permission.id)
        .where(Permission.scope_key == scope)
    )
    association = result.scalar_one_or_none()
    assert association is None


async def test_revoke_permission_role_not_found(client: AsyncClient, admin_token):
    """Test revoking permission from non-existent role returns 404."""
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    scope = "posts:delete"

    response: Response = await client.delete(
        f"/api/v1/admin/roles/{non_existent_id}/permissions/{scope}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404
    data = response.json()
    assert "Role not found" in data["detail"]


async def test_revoke_permission_permission_not_found(
    client: AsyncClient, admin_token, viewer_role
):
    """Test revoking a non-existent permission returns 404."""
    scope = "nonexistent:permission"

    response: Response = await client.delete(
        f"/api/v1/admin/roles/{viewer_role.id}/permissions/{scope}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404
    data = response.json()
    assert "Permission not found" in data["detail"]


async def test_assign_role_to_user_success(
    client: AsyncClient, admin_token, regular_user, viewer_role, db
):
    """Test assigning a role to a user successfully."""
    # First, create a new role to assign
    role_data = {
        "name": "moderator",
        "description": "Can moderate content",
    }

    create_response = await client.post(
        "/api/v1/admin/roles",
        json=role_data,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_response.status_code == 201
    new_role_id = create_response.json()["id"]

    # Assign role to user
    assign_data = {"role_id": new_role_id}
    response: Response = await client.post(
        f"/api/v1/admin/users/{regular_user.id}/roles",
        json=assign_data,
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 201

    # Verify role was assigned
    from sqlalchemy import select

    result = await db.execute(
        select(UserRole).where(
            UserRole.user_id == regular_user.id, UserRole.role_id == new_role_id
        )
    )
    user_role = result.scalar_one_or_none()
    assert user_role is not None


async def test_assign_role_to_user_user_not_found(client: AsyncClient, admin_token):
    """Test assigning role to non-existent user returns 404."""
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    assign_data = {"role_id": "00000000-0000-0000-0000-000000000001"}

    response: Response = await client.post(
        f"/api/v1/admin/users/{non_existent_id}/roles",
        json=assign_data,
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404
    data = response.json()
    assert "User not found" in data["detail"]


async def test_assign_role_to_user_role_not_found(
    client: AsyncClient, admin_token, regular_user
):
    """Test assigning non-existent role returns 404."""
    non_existent_id = "00000000-0000-0000-0000-000000000000"
    assign_data = {"role_id": non_existent_id}

    response: Response = await client.post(
        f"/api/v1/admin/users/{regular_user.id}/roles",
        json=assign_data,
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404
    data = response.json()
    assert "Role not found" in data["detail"]


async def test_revoke_role_from_user_success(
    client: AsyncClient, admin_token, regular_user, db
):
    """Test revoking a role from a user successfully."""
    # First, create a role and assign it

    new_role = Role(
        name="temp_role",
        description="Temporary role for testing",
        is_system=False,
        created_by=regular_user.id,  # Use existing user ID
    )
    db.add(new_role)
    await db.commit()
    await db.refresh(new_role)

    # Assign role to user via the API
    assign_data = {"role_id": str(new_role.id)}
    assign_response = await client.post(
        f"/api/v1/admin/users/{regular_user.id}/roles",
        json=assign_data,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert assign_response.status_code == 201

    # Now revoke it
    response: Response = await client.delete(
        f"/api/v1/admin/users/{regular_user.id}/roles/{new_role.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 204

    # Verify role was revoked
    from sqlalchemy import select

    result = await db.execute(
        select(UserRole).where(
            UserRole.user_id == regular_user.id, UserRole.role_id == new_role.id
        )
    )
    user_role = result.scalar_one_or_none()
    assert user_role is None


async def test_revoke_role_from_user_user_not_found(client: AsyncClient, admin_token):
    """Test revoking role from non-existent user returns 404."""
    non_existent_user = "00000000-0000-0000-0000-000000000000"
    role_id = "00000000-0000-0000-0000-000000000001"

    response: Response = await client.delete(
        f"/api/v1/admin/users/{non_existent_user}/roles/{role_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404
    data = response.json()
    assert "User not found" in data["detail"]


async def test_revoke_role_from_user_role_not_found(
    client: AsyncClient, admin_token, regular_user
):
    """Test revoking non-existent role returns 404."""
    non_existent_role = "00000000-0000-0000-0000-000000000000"

    response: Response = await client.delete(
        f"/api/v1/admin/users/{regular_user.id}/roles/{non_existent_role}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 404
    data = response.json()
    assert "Role not found" in data["detail"]


async def test_get_audit_logs_success(client: AsyncClient, admin_token, db):
    """Test retrieving audit logs with pagination."""
    # Create some audit logs directly
    from datetime import datetime, timezone
    from uuid import uuid4

    now = datetime.now(timezone.utc)
    logs = [
        AuditLog(
            actor_id=None,
            action="ROLE_CREATED",
            entity_type="Role",
            entity_id=str(uuid4()),  # Use valid UUID
            payload={"name": "test_role"},
            created_at=now,
        ),
        AuditLog(
            actor_id=None,
            action="USER_ROLE_ASSIGNED",
            entity_type="UserRole",
            entity_id=str(uuid4()),  # Use valid UUID
            payload={"user": "testuser", "role": "test_role"},
            created_at=now,
        ),
    ]

    for log in logs:
        db.add(log)
    await db.commit()

    response: Response = await client.get(
        "/api/v1/admin/audit-logs?page=1&page_size=20",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # May include other logs

    # Check structure of first log
    first_log = data[0]
    assert "id" in first_log
    assert "action" in first_log
    assert "entity_type" in first_log
    assert "entity_id" in first_log
    assert "payload" in first_log
    assert "created_at" in first_log


async def test_get_audit_logs_pagination(client: AsyncClient, admin_token, db):
    """Test pagination of audit logs."""
    # Create multiple logs
    from datetime import datetime, timezone
    from uuid import uuid4

    now = datetime.now(timezone.utc)
    for i in range(5):
        log = AuditLog(
            actor_id=None,
            action=f"TEST_ACTION_{i}",
            entity_type="Test",
            entity_id=str(uuid4()),  # Use valid UUID
            payload={"index": i},
            created_at=now,
        )
        db.add(log)
    await db.commit()

    # Get page 1 with page_size=2
    response: Response = await client.get(
        "/api/v1/admin/audit-logs?page=1&page_size=2",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


async def test_admin_routes_require_super_user(client: AsyncClient, mock_jwt):
    """Test that admin endpoints require super user privileges."""
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4

    import jwt

    from app.config import settings

    # Build payload for a regular user (not super user)
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload = {
        "sub": str(uuid4()),  # Random user ID
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": expire,
        "jti": str(uuid4()),
        "username": "regularuser",
        "roles": ["viewer"],
        "permissions": ["users:read"],
        "is_super_user": False,  # Not a super user
    }

    # Generate a real JWT token using the test private key
    regular_token = jwt.encode(
        payload, mock_jwt.private_key, algorithm=settings.jwt_algorithm
    )

    # Try to access admin endpoint
    response: Response = await client.post(
        "/api/v1/admin/roles",
        json={"name": "test", "description": "test"},
        headers={"Authorization": f"Bearer {regular_token}"},
    )

    assert response.status_code == 403
    data = response.json()
    assert "Super user privileges required" in data["detail"]
