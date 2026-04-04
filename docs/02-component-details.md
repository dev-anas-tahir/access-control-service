# Component Details

## API Layer (`app/api/v1/`)

The API layer is responsible for HTTP request handling, validation, authentication, and response formatting. All endpoints are mounted under the `/api/v1` prefix, except JWKS which is at the root.

### Authentication Endpoints (`auth.py`)

**Router Prefix**: `/auth`

#### `POST /auth/signup`

**Description**: Register a new user account with username and password. Automatically assigns the 'viewer' role upon successful creation.

**Authentication**: None (public endpoint)

**Request Body** (`SignupRequest`):
```json
{
  "username": "johndoe",
  "password": "SecurePass123!",
  "email": "john@example.com"
}
```

**Response** (201 Created) (`UserResponse`):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "johndoe",
  "email": "john@example.com",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Username or email already exists, password validation failure
- `422 Unprocessable Entity`: Invalid request body (Pydantic validation)

**Implementation Notes** (`app/api/v1/auth.py:14-68`):
- Applies `rate_limit_by_ip` dependency
- Validates username/email uniqueness via `AuthService.signup()`
- Password hashed with bcrypt
- 'viewer' role assigned automatically (seeded separately)
- Returns `UserResponse` with `from_attributes=True`

---

#### `POST /auth/login`

**Description**: Authenticate user with username/password and issue tokens.

**Authentication**: None

**Request Body** (`LoginRequest`):
```json
{
  "username": "johndoe",
  "password": "SecurePass123!"
}
```

**Response** (200 OK) (`TokenResponse`):
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer"
}
```

**Cookies Set**:
- `refresh_token`: httpOnly, secure (production), sameSite=lax, 7-day expiry

**Error Responses**:
- `401 Unauthorized`: Invalid credentials
- `429 Too Many Requests`: Rate limit exceeded (IP or username)

**Implementation Notes** (`app/api/v1/auth.py:71-118`):
- Applies both `rate_limit_by_ip` and `rate_limit_by_username`
- Calls `AuthService.login()` which:
  - Verifies password (triggers lazy bcrypt migration if needed)
  - Generates access token with roles/permissions claims
  - Generates refresh token (64 bytes URL-safe)
  - Stores refresh token in Redis: `refresh_token:{token}` → `user_id`
- Redis key expires in 7 days (configurable)
- Access token returned in body, refresh token in httpOnly cookie

---

#### `POST /auth/refresh`

**Description**: Obtain a new access token using the refresh token cookie. Implements refresh token rotation.

**Authentication**: None (refresh token validated via cookie)

**Request Body**: None

**Response** (200 OK) (`TokenResponse`):
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer"
}
```

**Cookies Set**:
- `refresh_token`: New rotated refresh token (same settings as login)

**Error Responses**:
- `401 Unauthorized`: Invalid, missing, or expired refresh token; JTI revoked

**Implementation Notes** (`app/api/v1/auth.py:121-166`):
- Applies `rate_limit_by_ip` dependency
- Extracts `refresh_token` from request cookies
- Calls `AuthService.refresh_token()`:
  - Validates token exists in Redis (`refresh_token:{token}`)
  - Loads user with roles/permissions
  - Creates new access token
  - Deletes old refresh token from Redis
  - Stores new refresh token with user_id mapping
- Response includes new access token, new refresh token sent as cookie

---

#### `POST /auth/logout`

**Description**: Invalidate the refresh token and revoke the current access token.

**Authentication**: Required (valid access token)

**Request Body**: None

**Response** (204 No Content)

**Implementation Notes** (`app/api/v1/auth.py:169-192`):
- Requires `get_current_user` dependency
- Extracts `refresh_token` from cookies
- Calls `AuthService.logout()`:
  - Deletes `refresh_token:{token}` from Redis
  - Stores JTI in revocation set: `revoked_jti:{jti}` with TTL = remaining token exp
- Returns empty 204 response

---

#### `GET /auth/me`

**Description**: Retrieve current user information including roles and permissions.

**Authentication**: Required (valid access token)

**Response** (200 OK) (`MeResponse`):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "johndoe",
  "roles": ["viewer", "editor"],
  "permissions": ["users:read", "posts:write"],
  "is_super_user": false
}
```

**Implementation Notes** (`app/api/v1/auth.py:195-217`):
- Requires `get_current_user` dependency
- Returns flattened list of role names and permission scope_keys
- `is_super_user` flag indicates admin override capability
- Response uses `MeResponse` schema

---

### Administrative Endpoints (`admin.py`)

**Router Prefix**: `/admin`

**Prerequisites**: All endpoints require `require_super_user` dependency (user must have `is_super_user=True` in JWT).

#### `POST /admin/roles`

**Description**: Create a new role (system roles are protected from deletion).

**Authentication**: Super user required

**Request Body** (`RoleCreate`):
```json
{
  "name": "editor",
  "description": "Can edit content"
}
```

**Response** (201 Created) (`RoleResponse`):
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "name": "editor",
  "description": "Can edit content",
  "is_system": false,
  "created_by": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-01-15T11:00:00Z"
}
```

**Implementation Notes** (`app/api/v1/admin.py:16-63`):
- Calls `RBACService.create_role()` with `actor_id` from JWT payload `sub`
- Validates role name uniqueness
- Writes audit log entry (action=`ROLE_CREATED`)

---

#### `DELETE /admin/roles/{role_id}`

**Description**: Soft delete a role. System roles (`is_system=True`) cannot be deleted.

**Authentication**: Super user required

**Path Parameters**:
- `role_id` (UUID)

**Response** (204 No Content)

**Error Responses**:
- `404 Not Found`: Role does not exist
- `403 Forbidden`: Attempt to delete system role

**Implementation Notes** (`app/api/v1/admin.py:66-89`):
- Role ID parsed as UUID by FastAPI path parameter
- Calls `RBACService.delete_role()`:
  - Sets `is_deleted=True`, `deleted_at=now()`
  - Does not physically delete row
  - Association cleanup via CASCADE on foreign keys

---

#### `POST /admin/roles/{role_id}/permissions`

**Description**: Grant a permission to a role. If the permission does not exist, it is auto-created.

**Authentication**: Super user required

**Path Parameters**:
- `role_id` (UUID)

**Request Body** (`PermissionCreate`):
```json
{
  "resource": "users",
  "action": "read"
}
```

**Response** (201 Created) (`RolePermissionResponse`):
```json
{
  "role_id": "660e8400-e29b-41d4-a716-446655440001",
  "permission_id": "770e8400-e29b-41d4-a716-446655440002",
  "granted_by": "550e8400-e29b-41d4-a716-446655440000",
  "granted_at": "2025-01-15T11:15:00Z"
}
```

**Implementation Notes** (`app/api/v1/admin.py:92-147`):
- Permission auto-generation: `scope_key = f"{resource}:{action}"`
- Creates Permission if not exists (checked via direct DB query to avoid stale session)
- Creates RolePermission association
- Audit log action=`PERMISSION_GRANTED`

---

#### `DELETE /admin/roles/{role_id}/permissions/{scope}`

**Description**: Revoke a permission from a role by its scope key.

**Authentication**: Super user required

**Path Parameters**:
- `role_id` (UUID)
- `scope` (string) - Format: `resource:action`

**Response** (204 No Content)

**Implementation Notes** (`app/api/v1/admin.py:150-182`):
- Scope key used to look up Permission by `Permission.scope_key`
- Deletes RolePermission association row
- Audit log action=`PERMISSION_REVOKED`

---

#### `POST /admin/users/{user_id}/roles`

**Description**: Assign a role to a user.

**Authentication**: Super user required

**Path Parameters**:
- `user_id` (UUID)

**Request Body** (`AssignRoleRequest`):
```json
{
  "role_id": "660e8400-e29b-41d4-a716-446655440001"
}
```

**Response** (201 Created) (`UserRoleResponse`):
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "role_id": "660e8400-e29b-41d4-a716-446655440001",
  "assigned_by": "550e8400-e29b-41d4-a716-446655440000",
  "assigned_at": "2025-01-15T11:30:00Z"
}
```

**Implementation Notes** (`app/api/v1/admin.py:185-224`):
- Creates UserRole association
- Audit log action=`USER_ROLE_ASSIGNED`
- Returns association record with timestamps

---

#### `DELETE /admin/users/{user_id}/roles/{role_id}`

**Description**: Remove a role from a user.

**Authentication**: Super user required

**Path Parameters**:
- `user_id` (UUID)
- `role_id` (UUID)

**Response** (204 No Content)

**Implementation Notes** (`app/api/v1/admin.py:227-264`):
- Deletes UserRole association
- Audit log action=`USER_ROLE_REVOKED`

---

#### `GET /admin/audit-logs`

**Description**: Retrieve paginated audit log entries.

**Authentication**: Super user required

**Query Parameters**:
- `page` (integer, default=1, minimum=1)
- `page_size` (integer, default=20, maximum=100)

**Response** (200 OK) (`list[AuditLogResponse]`):
```json
[
  {
    "id": "880e8400-e29b-41d4-a716-446655440005",
    "actor_id": "550e8400-e29b-41d4-a716-446655440000",
    "action": "ROLE_CREATED",
    "entity_type": "role",
    "entity_id": "660e8400-e29b-41d4-a716-446655440001",
    "payload": {
      "name": "editor",
      "description": "Can edit content"
    },
    "created_at": "2025-01-15T11:00:00Z"
  }
]
```

**Implementation Notes** (`app/api/v1/admin.py:267-291`):
- Calls `RBACService.get_audit_logs()` with pagination
- Offset calculated as `(page - 1) * page_size`
- Results ordered by `created_at DESC`
- Audit log `payload` stored as JSONB, returned as `dict | None`

---

### JWKS Endpoint (`jwks.py`)

**Mount Point**: `/.well-known/jwks.json` (mounted at root level)

**Description**: Serve the RSA public key in JWK (JSON Web Key) format for JWT signature verification by external clients.

**Authentication**: None (public endpoint)

**Response** (200 OK):
```json
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "kid": "a1b2c3d4e5f67890",
      "n": "xGOr-H7A5-YOUR-ACTUAL-KEY-HERE",
      "e": "AQAB"
    }
  ]
}
```

**Key Details**:
- `kty` (key type): "RSA"
- `use` (public key use): "sig" (signature)
- `kid` (key ID): SHA-256 hash of DER-encoded public key, truncated to 16 characters, base64url-encoded
- `n` (modulus): Base64url-encoded big-endian integer from RSA public key (no padding)
- `e` (exponent): Base64url-encoded exponent (usually 65537 = "AQAB")

**Implementation Notes** (`app/api/v1/jwks.py:13-59`):
- Loads RSA public key from `key_pair.public_key`
- Uses `public_numbers().n` and `public_numbers().e` to extract modulus and exponent
- Custom `base64url_encode()` function without padding (RFC 7515 Section 2)
- Supports algorithm "RSA" in `kty` and `use` fields
- `kid` is deterministic based on key content (enables key rotation)

---

## Service Layer (`app/services/`)

### `AuthService` (`auth_service.py`)

**Constructor**: No state, all methods static-like (no `self` except `cls` on classmethod)

#### `signup(db: AsyncSession, data: SignupRequest) -> User`

**Purpose**: Create new user account and assign default role.

**Algorithm**:
1. Check `username` uniqueness (query `User` where `username == data.username` and `is_deleted=False`)
2. If `data.email` provided, check email uniqueness
3. Hash password with `security.hash_password(data.password)` → `password_hash`
4. Create `User` instance:
   ```python
   user = User(
       username=data.username,
       email=data.email,
       password_hash=password_hash,
       is_active=True,
   )
   session.add(user)
   ```
5. `await session.flush()` to generate `user.id` without commit
6. Load 'viewer' role: `stmt = select(Role).where(Role.name == "viewer" and not is_deleted)`
7. If viewer role missing, raise `RuntimeError("Default viewer role not found. Seed the database.")`
8. Create `UserRole` association: `user_roles.insert().values(user_id=user.id, role_id=viewer_role.id)`
9. `await session.flush()` again
10. `await session.refresh(user)` with `selectinload(User.roles)` to load roles
11. Return `user` object (caller typically commits)

**Exceptions**:
- `UniquenessError`: Username or email already exists
- `RuntimeError`: Viewer role not found (requires database seeding)

**File**: `app/services/auth_service.py:39-106`

---

#### `login(db: AsyncSession, data: LoginRequest) -> tuple[str, str]`

**Purpose**: Authenticate credentials, issue tokens, store refresh token.

**Algorithm**:
1. Query user with roles and permissions via eager loading:
   ```python
   stmt = (
       select(User)
       .options(selectinload(User.roles).selectinload(Role.permissions))
       .where(User.username == data.username, User.is_deleted == False)
   )
   ```
2. If user not found or password invalid: still perform `verify_password()` (timing attack safe) but return generic "Invalid credentials"
3. `user = result.scalar_one_or_none()`
4. `if not user or not security.verify_password(data.password, user.password_hash): raise InvalidCredentialsError`
5. **Lazy bcrypt migration**: `if security.needs_rehash(user.password_hash):`
   - `user.password_hash = security.hash_password(data.password)`
   - Mark user as dirty for update
6. Collect roles: `[role.name for role in user.roles]`
7. Collect permissions: flatten all `permission.scope_key` from all roles
8. Create access token payload with `user.id`, `username`, `roles`, `permissions`, `is_super_user`
9. `access_token = security.create_access_token(payload)`
10. Generate refresh token: `refresh_token = secrets.token_urlsafe(64)`
11. Store in Redis: `await redis_client.setex(f"refresh_token:{refresh_token}", ttl_seconds, str(user.id))`
12. Return `(access_token, refresh_token)`

**Returns**: `(access_token: str, refresh_token: str)`

**Exceptions**:
- `InvalidCredentialsError`: Wrong username/password

**File**: `app/services/auth_service.py:109-177`

---

#### `refresh_token(db: AsyncSession, refresh_token: str) -> tuple[str, str]`

**Purpose**: Rotate refresh token and issue new access token.

**Algorithm**:
1. Lookup user ID from Redis: `user_id_str = await redis_client.get(f"refresh_token:{refresh_token}")`
2. If `None`: refresh token invalid or expired → `raise InvalidTokenError("Refresh token not found")`
3. `user_id = UUID(user_id_str)`
4. Query user with roles/permissions (same eager loading as login)
5. `user = await session.get(User, user_id)` with selectinload
6. If user not found, soft deleted, or inactive → `raise InvalidTokenError("User not found")`
7. Build new access token payload (roles/permissions recomputed)
8. `new_access_token = security.create_access_token(payload)`
9. Generate `new_refresh_token = secrets.token_urlsafe(64)`
10. **Rotate**: Delete old token: `await redis_client.delete(f"refresh_token:{refresh_token}")`
11. Store new: `await redis_client.setex(f"refresh_token:{new_refresh_token}", ttl_seconds, str(user.id))`
12. Return `(new_access_token, new_refresh_token)`

**Returns**: `(access_token, refresh_token)`

**Exceptions**:
- `InvalidTokenError`: Refresh token missing, user invalid

**File**: `app/services/auth_service.py:180-240`

---

#### `logout(refresh_token: str, payload: dict) -> None`

**Purpose**: Revoke refresh token and current access token.

**Algorithm**:
1. Delete refresh token from Redis: `await redis_client.delete(f"refresh_token:{refresh_token}")`
2. Extract `jti` from token payload dict (from `get_current_user` dependency)
3. Calculate TTL: remaining lifetime of access token
   - `exp = payload["exp"]` (UTC timestamp)
   - `now = int(time.time())`
   - `ttl_seconds = max(0, exp - now)`
4. Store JTI in revocation set: `await redis_client.setex(f"revoked_jti:{jti}", ttl_seconds, "1")`
5. Return `None` (caller returns 204)

**Returns**: None

**File**: `app/services/auth_service.py:243-269`

---

### `RBACService` (`rbac_service.py`)

**Helper**: `_write_audit_log(db, actor_id, action, entity_type, entity_id, payload)` (`app/services/rbac_service.py:22-41`)
- Creates `AuditLog` instance and adds to session
- `entity_id` converted to string if `UUID`
- `payload` defaults to empty dict
- **Does not commit** - caller is responsible for `session.commit()`

#### `create_role(db, data: RoleCreate, actor_id: UUID) -> Role`

Creates new role with audit trail.

**Algorithm**:
1. Check role name uniqueness (query `Role` where `name == data.name` and `is_deleted=False`)
2. Create `Role(name=data.name, description=data.description, created_by=actor_id)`
3. `session.add(role)`
4. `await session.flush()`
5. `await session.refresh(role)`
6. `_write_audit_log(db, actor_id, "ROLE_CREATED", "role", role.id, {"name": data.name, "description": data.description})`
7. Return `role`

**Exceptions**: `UniquenessError`

---

#### `delete_role(db, role_id: UUID, actor_id: UUID) -> None`

Soft deletes role, prevents deletion of system roles.

**Algorithm**:
1. `role = await session.get(Role, role_id)`
2. If not found or `is_deleted=True`: raise `NotFoundError("Role not found")`
3. If `role.is_system == True`: raise `SystemRoleError("Cannot delete system role")`
4. `role.is_deleted = True`
5. `role.deleted_at = datetime.utcnow()`
6. `_write_audit_log(db, actor_id, "ROLE_DELETED", "role", role_id, None)`
7. Return `None`

**Exceptions**: `NotFoundError`, `SystemRoleError`

---

#### `assign_permission(db, role_id: UUID, data: PermissionCreate, actor_id: UUID) -> RolePermission`

Grant permission to role, auto-creating permission if it doesn't exist.

**Algorithm**:
1. Load role with permissions: `result = await session.execute(select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id))`
2. `role = result.scalar_one_or_none()`; raise `NotFoundError` if missing or deleted
3. Compute `scope_key = f"{data.resource.strip()}:{data.action.strip()}"` (trim whitespace)
4. Check if permission already exists:
   `stmt = select(Permission).where(Permission.scope_key == scope_key)`
   - If exists: `permission = result.scalar_one()`
   - Else: create new `Permission(resource=data.resource, action=data.action, scope_key=scope_key)`, add to session, flush, refresh
5. Check for existing association (avoid duplicate):
   `stmt = select(RolePermission).where(RolePermission.role_id == role_id, RolePermission.permission_id == permission.id)`
   - If exists: raise `AlreadyAssignedError("Permission already granted to role")`
6. Create association:
   ```python
   role_perm = RolePermission(
       role_id=role_id,
       permission_id=permission.id,
       granted_by=actor_id
   )
   session.add(role_perm)
   ```
7. `_write_audit_log(db, actor_id, "PERMISSION_GRANTED", "role_permission", role_perm.id, {"role_id": str(role_id), "permission_scope": scope_key})`
8. Return `role_perm`

**Exceptions**: `NotFoundError`, `AlreadyAssignedError`

---

#### `revoke_permission(db, role_id: UUID, scope: str, actor_id: UUID) -> None`

Revoke permission from role by scope key.

**Algorithm**:
1. Load role with permissions via join with Permission:
   ```python
   stmt = (
       select(Role)
       .join(Role.permissions)
       .where(Role.id == role_id, Permission.scope_key == scope)
       .options(selectinload(Role.permissions))
   )
   ```
2. `role = result.scalar_one_or_none()`; if missing: raise `NotFoundError("Role or permission not found")`
3. Find permission object in `role.permissions` where `p.scope_key == scope`
4. If not found: raise `NotFoundError`
5. Delete association: `await session.execute(delete(RolePermission).where(RolePermission.role_id == role_id, RolePermission.permission_id == permission.id))`
6. `_write_audit_log(db, actor_id, "PERMISSION_REVOKED", "role", role_id, {"scope": scope})`
7. Return `None`

**Exceptions**: `NotFoundError`

---

#### `assign_role_to_user(db, user_id: UUID, role_id: UUID, actor_id: UUID) -> UserRole`

Assign role to user.

**Algorithm**:
1. Validate user exists and not deleted: `user = await session.get(User, user_id)`; if not/inactive raise `NotFoundError`
2. Validate role exists and not deleted: `role = await session.get(Role, role_id)`; if not/deleted raise `NotFoundError`
3. Check existing association:
   `stmt = select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)`
   - If exists: raise `AlreadyAssignedError("Role already assigned to user")`
4. Create association:
   ```python
   user_role = UserRole(
       user_id=user_id,
       role_id=role_id,
       assigned_by=actor_id
   )
   session.add(user_role)
   ```
5. `_write_audit_log(db, actor_id, "USER_ROLE_ASSIGNED", "user_role", user_role.id, {"user_id": str(user_id), "role_id": str(role_id)})`
6. Return `user_role`

**Exceptions**: `NotFoundError`, `AlreadyAssignedError`

---

#### `revoke_role_from_user(db, user_id: UUID, role_id: UUID, actor_id: UUID) -> None`

Remove role from user.

**Algorithm**:
1. Validate user exists (no soft delete check - can revoke even if deleted)
   `user = await session.get(User, user_id)`; raise `NotFoundError` if missing
2. Validate role exists and not deleted: `role = await session.get(Role, role_id)`; if not/deleted raise `NotFoundError`
3. Delete association:
   `await session.execute(delete(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id))`
   - Check `rowcount > 0`; if 0, raise `NotFoundError("Role not assigned to user")`
4. `_write_audit_log(db, actor_id, "USER_ROLE_REVOKED", "user_role", None, {"user_id": str(user_id), "role_id": str(role_id)})`
5. Return `None`

**Exceptions**: `NotFoundError`

---

#### `get_audit_logs(db, page: int = 1, page_size: int = 20) -> list[AuditLog]`

Retrieve paginated audit logs, newest first.

**Algorithm**:
1. Validate `page >= 1`, `page_size` between 1 and 100 (otherwise raise `ValueError` - though not explicitly checked)
2. `offset = (page - 1) * page_size`
3. Query:
   ```python
   stmt = (
       select(AuditLog)
       .order_by(AuditLog.created_at.desc())
       .offset(offset)
       .limit(page_size)
   )
   ```
4. `result = await session.execute(stmt)`
5. Return `result.scalars().all()`

**File**: `app/services/rbac_service.py:274-292`

---

## Data Layer (`app/models/`)

### Base Classes (`base.py`)

#### `Base`
- Inherits from `DeclarativeBase`
- Metadata configuration (not shown)

#### `TimestampMixin`
Provides automatic timestamp columns with database defaults.

**Columns**:
- `created_at`: `DateTime(timezone=True), server_default=func.now()`
- `updated_at`: `DateTime(timezone=True), server_default=func.now(), server_onupdate=FetchedValue()`

**Note**: `server_onupdate=FetchedValue()` ensures database updates timestamp on row update.

#### `SoftDeleteMixin`
Provides soft deletion columns (logical delete).

**Columns**:
- `is_deleted`: `Boolean, server_default=text("false"), nullable=False`
- `deleted_at`: `DateTime(timezone=True), nullable=True`

**Usage**: Inherited by `User` and `Role` models.

---

### User Model (`user.py`)

**Table Name**: `users`

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` | `primary_key=True`, `server_default=gen_random_uuid()` | Unique identifier |
| `username` | `String(255)` | `unique=True`, `nullable=False` | Login username |
| `email` | `String(255)` | `unique=True`, `nullable=True` | Optional email |
| `password_hash` | `String(255)` | `nullable=False` | Bcrypt hash |
| `is_super_user` | `Boolean` | `server_default=text("false")` | Super user privilege |
| `is_active` | `Boolean` | `server_default=text("true")` | Account enabled |
| `organization_id` | `UUID` | `nullable=True` | Optional org reference (no FK) |
| `created_at` | `DateTime` | From `TimestampMixin` | Created timestamp |
| `updated_at` | `DateTime` | From `TimestampMixin` | Updated timestamp |
| `is_deleted` | `Boolean` | From `SoftDeleteMixin` | Soft delete flag |
| `deleted_at` | `DateTime` | From `SoftDeleteMixin` | Deletion timestamp |

**Relationships**:
- `roles`: Many-to-many → `Role` via `user_roles` association
  - `relationship("Role", secondary=user_roles, back_populates="users")`

**File**: `app/models/user.py:1-50`

---

### Role Model (`role.py`)

**Table Name**: `roles`

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` | `primary_key=True`, `server_default=gen_random_uuid()` | Unique identifier |
| `name` | `String(100)` | `unique=True`, `nullable=False` | Role name (e.g., "admin", "viewer") |
| `description` | `Text` | `nullable=True` | Human-readable description |
| `is_system` | `Boolean` | `server_default=text("false")` | Protected from deletion |
| `created_by` | `UUID` | `ForeignKey("users.id", ondelete="SET NULL")`, `nullable=True` | Creator user ID |
| `created_at` | `DateTime` | From `TimestampMixin` | Created timestamp |
| `updated_at` | `DateTime` | From `TimestampMixin` | Updated timestamp |
| `is_deleted` | `Boolean` | From `SoftDeleteMixin` | Soft delete flag |
| `deleted_at` | `DateTime` | From `SoftDeleteMixin` | Deletion timestamp |

**Relationships**:
- `users`: Many-to-many → `User` via `user_roles`
- `permissions`: Many-to-many → `Permission` via `role_permissions`

**File**: `app/models/role.py:1-81`

---

### Permission Model (`role.py`)

**Table Name**: `permissions`

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` | `primary_key=True`, `server_default=gen_random_uuid()` | Unique identifier |
| `resource` | `String(100)` | `nullable=False` | Resource type (e.g., "users", "roles") |
| `action` | `String(100)` | `nullable=False` | Action (e.g., "read", "write", "delete") |
| `scope_key` | `String(255)` | `unique=True`, `nullable=False` | Composite `resource:action` |
| `created_at` | `DateTime` | `server_default=func.now()` | Creation timestamp |

**Note**: Does NOT inherit `TimestampMixin` or `SoftDeleteMixin`. Permissions are immutable once created (soft delete not supported). Only `created_at` present.

**Relationships**:
- `roles`: Many-to-many → `Role` via `role_permissions`

**File**: `app/models/role.py:68-81`

---

### Association Tables (`association.py`)

#### `user_roles`

**Table Name**: `user_roles`

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `user_id` | `UUID` | `ForeignKey("users.id", ondelete="CASCADE")`, `primary_key=True` | User reference |
| `role_id` | `UUID` | `ForeignKey("roles.id", ondelete="CASCADE")`, `primary_key=True` | Role reference |
| `assigned_by` | `UUID` | `ForeignKey("users.id", ondelete="SET NULL")`, `nullable=True` | Actor who assigned |
| `assigned_at` | `DateTime` | `server_default=func.now()` | Assignment timestamp |

**Note**: Composite primary key (`user_id`, `role_id`). No separate `id` column.

**File**: `app/models/association.py:1-39`

---

#### `role_permissions`

**Table Name**: `role_permissions`

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `role_id` | `UUID` | `ForeignKey("roles.id", ondelete="CASCADE")`, `primary_key=True` | Role reference |
| `permission_id` | `UUID` | `ForeignKey("permissions.id", ondelete="CASCADE")`, `primary_key=True` | Permission reference |
| `granted_by` | `UUID` | `ForeignKey("users.id", ondelete="SET NULL")`, `nullable=True` | Actor who granted |
| `granted_at` | `DateTime` | `server_default=func.now()` | Grant timestamp |

**Note**: Composite primary key (`role_id`, `permission_id`).

**File**: `app/models/association.py:41-55`

---

### AuditLog Model (`audit_log.py`)

**Table Name**: `audit_logs`

**Columns**:

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | `UUID` | `primary_key=True`, `server_default=gen_random_uuid()` | Unique identifier |
| `actor_id` | `UUID` | `ForeignKey("users.id", ondelete="SET NULL")`, `nullable=True` | Who performed action |
| `action` | `String(255)` | `nullable=False` | Action type enum (e.g., "ROLE_CREATED") |
| `entity_type` | `String(255)` | `nullable=False` | Type of entity affected ("role", "user", "permission", etc.) |
| `entity_id` | `UUID` | `nullable=True` | ID of affected entity |
| `payload` | `JSONB` | `nullable=True` | Additional context (dict, varied structure) |
| `created_at` | `DateTime` | `server_default=func.now()` | When action occurred |

**Notes**:
- PostgreSQL-specific `JSONB` type allows indexing and querying
- `entity_id` stored as UUID but may be interpreted as string in application code
- No soft delete - audit logs are immutable once written

**File**: `app/models/audit_log.py:1-32`

---

## Core Utilities (`app/core/`)

### Security (`security.py`)

#### Password Management

**`hash_password(password: str) -> str`**

Uses `passlib.CryptContext` configured with schemes `["bcrypt", "django_pbkdf2_sha256"]` and `deprecated="auto"`.

- New passwords: bcrypt with default rounds (typically 12)
- Legacy passwords (Django): automatically verified with `django_pbkdf2_sha256` and re-hashed to bcrypt on next login via `needs_rehash()`

**`verify_password(password: str, hashed: str) -> bool`**

- Delegates to `pwd_context.verify(password, hashed)`
- Works for both bcrypt and Django PBKDF2 hashes

**`needs_rehash(hashed: str) -> bool`**

- Returns `True` if hash uses deprecated scheme or rounds are below current settings
- Used for lazy migration during login

**File**: `app/core/security.py:13-30`

---

#### JWT Operations

**`create_access_token(user_id: UUID, username: str, roles: list[str], permissions: list[str], is_super_user: bool) -> str`**

Creates RS256-signed JWT with standard and custom claims.

**Payload Claims**:
- `sub` (subject): `str(user_id)`
- `iss` (issuer): from `settings.jwt_issuer` (default "access-control-service")
- `iat` (issued at): current UTC datetime with timezone
- `exp` (expiration): `iat + settings.jwt_access_token_expire_minutes` minutes
- `jti` (JWT ID): `str(uuid4())` - unique identifier for revocation
- `username`: string
- `roles`: list of role names
- `permissions`: list of permission scope keys
- `is_super_user`: boolean

**Algorithm**: RS256 with `key_pair.private_key` (loaded from PEM files)

**Return**: Encoded JWT string (compact serialization)

**File**: `app/core/security.py:33-59`

---

**`verify_access_token(token: str) -> dict`**

Decodes and validates JWT signature and claims.

**Validation**:
- Signature verification with `key_pair.public_key` and RS256
- Standard claims: `exp` (expiration), `nbf` (not before - not used), `iat` (issued at)
- Required custom claims: `sub`, `jti`, `iss`

**Raises**:
- `TokenExpiredError` (custom, wraps `ExpiredSignatureError`) if token expired
- `InvalidTokenError` (custom) for any other validation issue

**Returns**: Decoded payload dictionary

**File**: `app/core/security.py:61-81`

---

### Dependencies (`dependencies.py`)

#### `get_current_user(credentials: HTTPAuthorizationCredentials) -> TokenPayload`

FastAPI dependency that validates access token and checks revocation.

**Algorithm**:
1. Extract token: `credentials.credentials` from `Authorization: Bearer <token>`
2. `payload = verify_access_token(token)`
3. `jti = payload.get("jti")`
4. Check Redis: `await redis_client.get(f"revoked_jti:{jti}")`
   - If found: raise `HTTPException(401, "Token has been revoked")`
5. Return `TokenPayload` TypedDict (typed return value for downstream dependencies)

**Exceptions** (`HTTPException`):
- `401 Unauthorized`: Invalid token, expired, revoked, or malformed

**File**: `app/core/dependencies.py:14-45`

---

#### `require_super_user(payload: TokenPayload) -> TokenPayload`

Dependency that enforces super user privilege.

**Algorithm**:
1. `is_super = payload.get("is_super_user")`
2. If `not is_super`: raise `HTTPException(403, "Super user privilege required")`
3. Return `payload` unchanged

**Usage**: Applied to admin router endpoints via `dependencies=[Depends(require_super_user)]`

**File**: `app/core/dependencies.py:48-66`

---

### Rate Limiting (`rate_limit.py`)

#### Constants
- `IP_MAX_ATTEMPTS = 20` per `IP_WINDOW = 60` seconds
- `USERNAME_MAX_ATTEMPTS = 5` per `USERNAME_WINDOW = 300` seconds (5 minutes)

**File**: `app/core/rate_limit.py:1-12`

---

#### `rate_limit_by_ip(request: Request) -> None`

Rate limit by client IP address and endpoint path.

**Algorithm**:
1. Extract IP: `ip = request.client.host`
2. Build key: `key = f"rate_limit:ip:{ip}:{request.url.path}"`
3. Redis operations:
   - `count = await redis_client.incr(key)`
   - If `count == 1`: `await redis_client.expire(key, IP_WINDOW)` (set TTL on first request)
4. If `count > IP_MAX_ATTEMPTS`:
   - `retry_after = await redis_client.ttl(key)` (remaining seconds)
   - Raise `HTTPException(429, "Too many requests", headers={"Retry-After": str(retry_after)})`
5. If within limit: return `None` (no exception)

**Usage**: Applied to auth endpoints (`/signup`, `/login`, `/refresh`, `/logout`, `/me`) via dependency

**File**: `app/core/rate_limit.py:15-38`

---

#### `rate_limit_by_username(request: Request) -> None`

Rate limit by username for login endpoint (protect against username enumeration brute force).

**Algorithm**:
1. Read request body: `body_bytes = await request.body()` (consumes stream)
2. Parse JSON: `body = json.loads(body_bytes) if body_bytes else {}`
3. Extract `username = body.get("username", "").strip().lower()`
4. If empty: return `None` (skip rate limit)
5. Build key: `key = f"rate_limit:username:{username}:{request.url.path}"`
6. Same Redis INCR + expire pattern as IP rate limiting
7. Threshold: `USERNAME_MAX_ATTEMPTS = 5` over `USERNAME_WINDOW = 300`
8. Raise `HTTPException(429)` on violation

**File**: `app/core/rate_limit.py:41-70`

---

### Key Management (`keys.py`)

**`RSAKeyPair` Singleton**

Class with class-level `_instance` and `private_key`, `public_key` attributes.

**`load()` classmethod**:
- Reads private key from `settings.private_key_path`
- Reads public key from `settings.public_key_path`
- Uses `serialization.load_pem_private_key()` and `serialization.load_pem_public_key()` from `cryptography`
- Stores in class attributes
- Raises `RuntimeError` if files missing or invalid

**`get_key_pair()` classmethod**:
- Returns `(private_key, public_key)` tuple
- Lazy initialization: calls `load()` if not loaded

**Usage**: `from app.core.keys import key_pair; private_key, public_key = key_pair.get_key_pair()`

**File**: `app/core/keys.py:1-52`

---

### Logging (`logging.py`)

**`JSONFormatter`** for structured logging compatible with GCP Cloud Logging.

**Format**:
```json
{
  "timestamp": "2025-01-15T10:30:00.123Z",
  "severity": "INFO",
  "message": "...",
  "request_id": "uuid",
  "logger": "uvicorn",
  "extra_field1": "value1",
  ...
}
```

**Features**:
- RFC 3339 timestamps with Z suffix
- `severity` instead of `level`
- `request_id` injected from ContextVar (`app/core/context.py`)
- Non-standard LogRecord attributes included at top level
- Silences noisy loggers (SQLAlchemy, httpx, uvicorn.access)

**File**: `app/core/logging.py:1-128`

---

## Configuration (`config.py`)

**`Settings`** class inherits from `BaseSettings` with `SettingsConfigDict(env_file=BASE_DIR / ".env", case_sensitive=False)`.

**All Environment Variables**:

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `app_env` | `str` | "development" | Environment name |
| `app_debug` | `bool` | `False` | Debug mode (SQL log, reload) |
| `log_level` | `str` | "INFO" | Logging level |
| `database_url` | `PostgresDsn` | **Required** | Async PostgreSQL DSN |
| `test_database_url` | `PostgresDsn` | `None` | Test database URL |
| `pool_size` | `int` | 10 | DB connection pool size |
| `max_overflow` | `int` | 20 | Pool overflow allowance |
| `redis_url` | `RedisDsn` | **Required** | Redis connection URL |
| `jwt_algorithm` | `str` | "RS256" | JWT signing algorithm |
| `jwt_issuer` | `str` | "access-control-service" | JWT `iss` claim |
| `jwt_access_token_expire_minutes` | `int` | 15 | Access token TTL |
| `jwt_refresh_token_expire_days` | `int` | 7 | Refresh token TTL |
| `private_key_path` | `Path` | "keys/private_key.pem" | RSA private key path |
| `public_key_path` | `Path` | "keys/public.pem" | RSA public key path |
| `gcp_project_id` | `str` | **Required** | GCP project ID |
| `pubsub_topic_id` | `str` | **Required** | Pub/Sub topic name |

**File**: `app/config.py:1-87`

---

## References

- API Implementation: `app/api/v1/auth.py:1-199`, `app/api/v1/admin.py:1-200`, `app/api/v1/jwks.py:1-72`
- Services: `app/services/auth_service.py:1-269`, `app/services/rbac_service.py:1-293`
- Models: `app/models/user.py`, `app/models/role.py`, `app/models/association.py`, `app/models/audit_log.py`, `app/models/base.py`
- Core: `app/core/security.py`, `app/core/dependencies.py`, `app/core/rate_limit.py`, `app/core/keys.py`
- Database: `app/db/session.py`, `app/db/redis.py`
