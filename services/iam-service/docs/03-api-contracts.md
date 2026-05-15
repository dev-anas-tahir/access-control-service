# API Contracts

## Base URL Pattern

```
Production: https://auth.yourdomain.com/api/v1
Development: http://localhost:8000/api/v1
```

All API endpoints return JSON and use standard HTTP status codes.

## Common Response Format

### Success Response
```json
{
  "data": { ... }  // or direct object
}
```

### Error Response
```json
{
  "detail": "Error message describing the problem"
}
```

## Authentication Endpoints

### 1. Sign Up

**Endpoint**: `POST /auth/signup`

**Description**: Register a new user account. Automatically assigns the 'viewer' role.

**Authentication**: None

**Request Body** (`SignupRequest`) - `app/auth/infrastructure/http/schemas.py`

```json
{
  "username": "johndoe",
  "password": "SecurePass123!",
  "email": "john@example.com"
}
```

**Field Constraints**:
- `username`: 3-50 characters, alphanumeric and special chars allowed
- `password`: Minimum 8 chars, must include uppercase, digit, and special character from `!@#$%^&*()_+-=[]{}|;':",<>,./?`
- `email`: Valid email format, optional

**Response** (201 Created)

**Schema**: `UserResponse` - `app/auth/infrastructure/http/schemas.py`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "johndoe",
  "email": "john@example.com",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Errors**:
- `400 Bad Request`: Username or email already exists; password validation failure
- `422 Unprocessable Entity`: Invalid request body (e.g., username too short)

---

### 2. Login

**Endpoint**: `POST /auth/login`

**Description**: Authenticate credentials and receive access token and refresh token cookie.

**Authentication**: None

**Request Body** (`LoginRequest`) - `app/auth/infrastructure/http/schemas.py`

```json
{
  "username": "johndoe",
  "password": "SecurePass123!"
}
```

**Response** (200 OK)

**Schema**: `TokenResponse` - `app/auth/infrastructure/http/schemas.py`

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer"
}
```

**Cookies Set**:
- `refresh_token`: httponly, secure (production), sameSite=lax, max-age=604800 (7 days)

**Headers**:
- `Set-Cookie: refresh_token=<token>; HttpOnly; Path=/; SameSite=Lax; Max-Age=604800` (development may set `Secure` only in production)

**Errors**:
- `401 Unauthorized`: Invalid credentials
- `429 Too Many Requests`: Rate limit exceeded

---

### 3. Refresh Token

**Endpoint**: `POST /auth/refresh`

**Description**: Exchange a valid refresh token for a new access token and new refresh token (rotation).

**Authentication**: None (refresh token validated via cookie)

**Request Body**: None

**Response** (200 OK)

**Schema**: `TokenResponse`

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIs...",
  "token_type": "bearer"
}
```

**Cookies Set**: New `refresh_token` cookie (old one invalidated)

**Errors**:
- `401 Unauthorized`: Missing, invalid, or expired refresh token

---

### 4. Logout

**Endpoint**: `POST /auth/logout`

**Description**: Invalidate refresh token and revoke current access token.

**Authentication**: Required (valid access token)

**Request Body**: None

**Response** (204 No Content)

**Headers**: `Set-Cookie: refresh_token=; Max-Age=0; Expires=Thu, 01 Jan 1970 00:00:00 GMT` (clear cookie)

**Implementation**: Revokes JTI in Redis and deletes refresh token mapping.

---

### 5. Get Current User

**Endpoint**: `GET /auth/me`

**Description**: Retrieve authenticated user's profile with roles and permissions.

**Authentication**: Required

**Response** (200 OK)

**Schema**: `MeResponse` - `app/auth/infrastructure/http/schemas.py`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "johndoe",
  "roles": ["viewer", "editor"],
  "permissions": ["users:read", "posts:write"],
  "is_super_user": false
}
```

---

## Administrative Endpoints

All admin endpoints require `is_super_user=True` in the JWT.

### 6. Create Role

**Endpoint**: `POST /admin/roles`

**Description**: Create a new role. System roles (`is_system=True`) are protected and cannot be modified.

**Authentication**: Super user required

**Request Body** (`RoleCreate`) - `app/rbac/infrastructure/http/schemas.py`

```json
{
  "name": "editor",
  "description": "Can edit content"
}
```

**Response** (201 Created)

**Schema**: `RoleResponse` - `app/rbac/infrastructure/http/schemas.py`

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

---

### 7. Delete Role

**Endpoint**: `DELETE /admin/roles/{role_id}`

**Description**: Soft delete a role. System roles cannot be deleted.

**Authentication**: Super user required

**Path Parameters**:
- `role_id`: UUID of role to delete

**Response** (204 No Content)

**Errors**:
- `404 Not Found`: Role not found or already deleted
- `403 Forbidden`: Attempt to delete system role

---

### 8. Assign Permission to Role

**Endpoint**: `POST /admin/roles/{role_id}/permissions`

**Description**: Grant a permission to a role. If the permission does not exist, it is automatically created.

**Authentication**: Super user required

**Path Parameters**:
- `role_id`: UUID of target role

**Request Body** (`PermissionCreate`) - `app/rbac/infrastructure/http/schemas.py`

```json
{
  "resource": "users",
  "action": "read"
}
```

**Response** (201 Created)

**Schema**: `RolePermissionResponse` - `app/rbac/infrastructure/http/schemas.py`

```json
{
  "role_id": "660e8400-e29b-41d4-a716-446655440001",
  "permission_id": "770e8400-e29b-41d4-a716-446655440002",
  "granted_by": "550e8400-e29b-41d4-a716-446655440000",
  "granted_at": "2025-01-15T11:15:00Z"
}
```

**Notes**:
- Permission `scope_key` is computed as `resource:action` (e.g., `"users:read"`)
- Duplicate assignment returns `409 Conflict` via `AlreadyAssignedError`

---

### 9. Revoke Permission from Role

**Endpoint**: `DELETE /admin/roles/{role_id}/permissions/{scope}`

**Description**: Remove a permission from a role.

**Authentication**: Super user required

**Path Parameters**:
- `role_id`: UUID of target role
- `scope`: Permission scope key in format `resource:action`

**Response** (204 No Content)

**Errors**:
- `404 Not Found`: Role not found or permission not assigned

---

### 10. Assign Role to User

**Endpoint**: `POST /admin/users/{user_id}/roles`

**Description**: Assign an existing role to a user.

**Authentication**: Super user required

**Path Parameters**:
- `user_id`: UUID of target user

**Request Body** (`AssignRoleRequest`) - `app/rbac/infrastructure/http/schemas.py`

```json
{
  "role_id": "660e8400-e29b-41d4-a716-446655440001"
}
```

**Response** (201 Created)

**Schema**: `UserRoleResponse` - `app/rbac/infrastructure/http/schemas.py`

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "role_id": "660e8400-e29b-41d4-a716-446655440001",
  "assigned_by": "550e8400-e29b-41d4-a716-446655440000",
  "assigned_at": "2025-01-15T11:30:00Z"
}
```

**Errors**:
- `404 Not Found`: User or role does not exist
- `409 Conflict`: Role already assigned to user

---

### 11. Revoke Role from User

**Endpoint**: `DELETE /admin/users/{user_id}/roles/{role_id}`

**Description**: Remove a role assignment from a user.

**Authentication**: Super user required

**Path Parameters**:
- `user_id`: UUID of target user
- `role_id`: UUID of role to remove

**Response** (204 No Content)

**Errors**:
- `404 Not Found`: User not found, role not found, or assignment does not exist

---

### 12. Get Audit Logs

**Endpoint**: `GET /admin/audit-logs`

**Description**: Retrieve paginated audit log entries for compliance and monitoring.

**Authentication**: Super user required

**Query Parameters**:
- `page` (integer, default=1, minimum=1): Page number
- `page_size` (integer, default=20, maximum=100): Items per page

**Response** (200 OK)

**Schema**: `list[AuditLogResponse]` - `app/audit/infrastructure/http/schemas.py`

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

**Audit Actions**:
- `ROLE_CREATED`
- `ROLE_DELETED`
- `PERMISSION_GRANTED`
- `PERMISSION_REVOKED`
- `USER_ROLE_ASSIGNED`
- `USER_ROLE_REVOKED`

**Entity Types**: `"role"`, `"role_permission"`, `"user_role"`

---

## JWKS Endpoint

### 13. JSON Web Key Set

**Endpoint**: `GET /.well-known/jwks.json`

**Description**: Public JWK endpoint for key discovery. Used by clients to verify JWT signatures.

**Authentication**: None

**Response** (200 OK)

**Schema**: `{"keys": [{...}]}` - JWK format per RFC 7517

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

**Key Fields**:
- `kty`: Key type ("RSA")
- `use`: Public key use ("sig" for signature)
- `kid`: Key identifier (SHA-256 hash of DER-encoded public key, truncated to 16 chars)
- `n`: Modulus (base64url-encoded without padding)
- `e`: Exponent (base64url-encoded, typically "AQAB" for 65537)

**File**: `app/auth/infrastructure/http/jwks.py`

---

## Pydantic Schema Reference

### `app/auth/infrastructure/http/schemas.py`

#### `SignupRequest` (Input)
```python
class SignupRequest(BaseModel):
    username: str  # 3-50 chars
    password: str  # validated by custom validator
    email: EmailStr | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        # Enforces complexity: 8+ chars, 1 uppercase, 1 digit, 1 special
```

#### `LoginRequest` (Input)
```python
class LoginRequest(BaseModel):
    username: str
    password: str
```

#### `TokenResponse` (Output)
```python
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

#### `UserResponse` (Output)
```python
class UserResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

#### `MeResponse` (Output)
```python
class MeResponse(BaseModel):
    id: UUID
    username: str
    roles: list[str]
    permissions: list[str]
    is_super_user: bool
    model_config = ConfigDict(from_attributes=True)
```

---

### `app/rbac/infrastructure/http/schemas.py`

#### `RoleCreate` (Input)
```python
class RoleCreate(BaseModel):
    name: str  # 3-100 chars, unique
    description: str | None = None
```

#### `RoleResponse` (Output)
```python
class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_system: bool
    created_by: UUID | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

#### `PermissionCreate` (Input)
```python
class PermissionCreate(BaseModel):
    resource: str  # 1-100 chars
    action: str    # 1-100 chars
```

#### `PermissionResponse` (Output)
```python
class PermissionResponse(BaseModel):
    id: UUID
    resource: str
    action: str
    scope_key: str  # computed: f"{resource}:{action}"
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

#### `AssignRoleRequest` (Input)
```python
class AssignRoleRequest(BaseModel):
    role_id: UUID
```

#### `AuditLogResponse` (Output)
```python
class AuditLogResponse(BaseModel):
    id: UUID
    actor_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    payload: dict | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

#### `RolePermissionResponse` (Output)
```python
class RolePermissionResponse(BaseModel):
    role_id: UUID
    permission_id: UUID
    granted_by: UUID | None
    granted_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

#### `UserRoleResponse` (Output)
```python
class UserRoleResponse(BaseModel):
    user_id: UUID
    role_id: UUID
    assigned_by: UUID | None
    assigned_at: datetime
    model_config = ConfigDict(from_attributes=True)
```

---

## Authentication Schemes

### Access Token
- **Type**: Bearer token (JWT)
- **Header**: `Authorization: Bearer <access_token>`
- **Lifetime**: 15 minutes (configurable)
- **Algorithm**: RS256
- **Claims**:
  ```json
  {
    "sub": "user-uuid-string",
    "iss": "access-control-service",
    "iat": 1736934600,
    "exp": 1736935500,
    "jti": "uuid",
    "username": "johndoe",
    "roles": ["viewer"],
    "permissions": ["users:read"],
    "is_super_user": false
  }
  ```

### Refresh Token
- **Type**: Random URL-safe string (64 bytes)
- **Storage**: httpOnly cookie named `refresh_token`
- **Lifetime**: 7 days (configurable)
- **Redis Key**: `refresh_token:{token}` → `user_id`
- **Rotation**: New refresh token issued on each refresh; old one deleted

---

## Rate Limiting

### Applied to
- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`

### IP-Based Limits
- 20 requests per 60 seconds per IP address
- Redis key: `rate_limit:ip:{ip}:{path}`
- HTTP 429 with `Retry-After` header on violation

### Username-Based Limits (Login Only)
- 5 failed attempts per 300 seconds per username
- Redis key: `rate_limit:username:{username}:/auth/login`
- HTTP 429 with `Retry-After` header on violation

---

## Error Codes and Messages

| Status Code | Condition | Example Detail Message |
|-------------|-----------|------------------------|
| 200 | Success (GET) | `{data}` |
| 201 | Success (POST) | `{data}` |
| 204 | Success (DELETE) | (empty body) |
| 400 | Validation error | "Username already exists" |
| 401 | Unauthorized | "Invalid credentials" or "Token has been revoked" |
| 403 | Forbidden | "Super user privilege required" |
| 404 | Not found | "Role not found" |
| 409 | Conflict | "Permission already granted to role" |
| 422 | Unprocessable Entity | Pydantic validation details |
| 429 | Too many requests | "Too many requests" with `Retry-After` header |
| 500 | Internal server error | Generic message (details logged) |

---

## Sample cURL Commands

```bash
# Sign up
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"username":"johndoe","password":"SecurePass123!","email":"john@example.com"}'

# Login (captures refresh token cookie)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"johndoe","password":"SecurePass123!"}' \
  -c cookies.txt

# Use access token to call protected endpoint
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"

# Refresh token (uses cookie from cookies.txt)
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -b cookies.txt -c cookies.txt

# Logout (uses cookie from cookies.txt)
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer <access_token>" \
  -b cookies.txt -c cookies.txt

# Create role (super user only)
curl -X POST http://localhost:8000/api/v1/admin/roles \
  -H "Authorization: Bearer <admin_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"editor","description":"Can edit content"}'

# Get JWKS
curl http://localhost:8000/.well-known/jwks.json
```

---

## References

- Auth routes: `app/auth/infrastructure/http/routes.py`
- RBAC routes: `app/rbac/infrastructure/http/routes.py`
- Audit routes: `app/audit/infrastructure/http/routes.py`
- JWKS: `app/auth/infrastructure/http/jwks.py`
- Auth schemas: `app/auth/infrastructure/http/schemas.py`
- RBAC schemas: `app/rbac/infrastructure/http/schemas.py`
- Audit schemas: `app/audit/infrastructure/http/schemas.py`
- Rate limiting: `app/shared/infrastructure/http/rate_limit.py`
- Authentication dependency: `app/auth/infrastructure/http/dependencies.py`
