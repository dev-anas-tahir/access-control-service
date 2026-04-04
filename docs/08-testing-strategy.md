# Testing Strategy

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures (Redis mock, JWT mock, DB engine)
├── unit/                    # Unit tests (fast, mocked dependencies)
│   ├── test_security.py
│   ├── test_rbac_service.py
│   ├── test_auth_service.py
│   ├── test_dependencies.py
│   ├── test_rate_limit.py
│   └── test_logging.py
└── integration/             # Integration tests (real DB, mocked external)
    ├── conftest.py          # Additional fixtures (integration DB override, admin token)
    ├── test_auth_routes.py
    ├── test_admin_routes.py
    └── test_jwks_routes.py
```

---

## Testing Stack

| Tool | Version | Purpose |
|------|---------|---------|
| `pytest` | Latest | Test runner |
| `pytest-asyncio` | Latest | Async test support |
| `httpx` | Latest | Async HTTP client |
| `pytest-mock` | Latest | Mocking utilities |
| `freezegun` | Optional | Time mocking |

**Configuration** (`pyproject.toml`):
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

---

## Unit Tests (`tests/unit/`)

### Characteristics
- **Fast**: < 1 second total
- **No external dependencies**: All DB, Redis, Pub/Sub calls mocked
- **Pure business logic**: Test service methods, security functions, dependencies, rate limiting
- **Isolated**: Each test independent, uses fixtures with mocks

### Common Patterns

**Mocking Database Session**:
```python
@pytest.fixture
def mock_db(mocker):
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    session.get = AsyncMock()
    return session
```

**Mocking Redis**:
```python
@pytest.fixture(scope="session")
def mock_redis(mocker):
    redis_mock = AsyncMock()
    redis_mock.get.return_value = None
    redis_mock.setex.return_value = True
    redis_mock.incr.return_value = 1
    redis_mock.delete.return_value = 1
    return redis_mock
```

**Mocking JWT**:
```python
@pytest.fixture(scope="session")
def mock_jwt(mocker):
    # Generate real RSA keys for valid signature
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return MagicMock(private_key=private_key, public_key=public_key)
```

---

### Example Unit Tests

#### `test_security.py` (`app/core/security.py`)

**What to test**:
- `hash_password()` produces different hashes each time (salt)
- `verify_password()` correctly validates known hash
- `needs_rehash()` detects old bcrypt rounds or deprecated scheme
- `create_access_token()` includes all required claims
- `verify_access_token()` accepts valid token, rejects expired/invalid

**Example**:
```python
@pytest.mark.asyncio
async def test_create_access_token_contains_roles():
    token = security.create_access_token(
        user_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        username="testuser",
        roles=["viewer", "editor"],
        permissions=["users:read", "posts:write"],
        is_super_user=False,
    )
    payload = security.verify_access_token(token)
    assert payload["roles"] == ["viewer", "editor"]
    assert payload["permissions"] == ["users:read", "posts:write"]
    assert payload["username"] == "testuser"
    assert payload["is_super_user"] is False
    assert "sub" in payload
    assert "exp" in payload
    assert "jti" in payload
```

---

#### `test_rbac_service.py` (`app/services/rbac_service.py`)

**What to test**:
- All service methods with various scenarios (success, not found, duplicate, system role deletion)
- Audit log writing (calls `_write_audit_log` with correct params)
- Transaction handling (session.commit not called inside service)
- Permission auto-creation logic

**Example**:
```python
@pytest.mark.asyncio
async def test_assign_permission_creates_missing_permission(mock_db):
    # Arrange: role exists, permission does NOT exist
    role_id = uuid4()
    role = Role(id=role_id, name="test_role", permissions=[])
    mock_db.get.return_value = role
    mock_db.execute.side_effect = [
        MagicMock(scalar_one_or_none=lambda: None),  # permission not found
        MagicMock(scalar_one_or_none=lambda: None),  # association not exists
    ]

    service = RBACService()
    data = PermissionCreate(resource="users", action="read")

    result = await service.assign_permission(mock_db, role_id, data, actor_id=uuid4())

    # Assert: permission created, association created
    assert mock_db.add.call_count >= 2  # Permission + RolePermission
    assert result.role_id == role_id
    assert result.permission_id is not None
```

---

#### `test_auth_service.py` (`app/services/auth_service.py`)

**What to test**:
- `signup`: uniqueness check, password hashing, viewer role assignment
- `login`: invalid credentials, valid login, lazy bcrypt migration trigger
- `refresh_token`: rotation, JWT creation, user loading
- `logout`: Redis deletion, JTI revocation TTL calculation

**Example - Logout JTI TTL**:
```python
@pytest.mark.asyncio
async def test_logout_revokes_token_with_correct_ttl(mock_db, mock_redis):
    # Arrange: access token expires in 300 seconds from now
    now = int(time.time())
    payload = {"exp": now + 300, "jti": "test-jti", "sub": "user123"}
    refresh_token = "old-refresh-token"

    mock_redis.get.return_value = b"user123"

    await auth_service.logout(refresh_token, payload)

    # Assert: JTI stored with TTL = 300
    mock_redis.setex.assert_called_once_with(
        "revoked_jti:test-jti", 300, "1"
    )
```

---

#### `test_dependencies.py` (`app/core/dependencies.py`)

**What to test**:
- `get_current_user`: valid token passes, invalid raises 401, revoked token raises 401
- `require_super_user`: super user passes, non-super raises 403

**Example**:
```python
@pytest.mark.asyncio
async def test_get_current_user_raises_401_for_revoked_token(mock_redis):
    # Arrange: token with jti that exists in revocation set
    token = "valid.signature.but.revoked"
    payload = {"sub": "user123", "jti": "revoked-jti", "exp": 9999999999}
    mock_redis.get.return_value = b"1"  # JTI is revoked

    with pytest.raises(HTTPException) as exc:
        await dependencies.get_current_user(token)

    assert exc.value.status_code == 401
    assert "revoked" in exc.value.detail.lower()
```

---

#### `test_rate_limit.py` (`app/core/rate_limit.py`)

**What to test**:
- IP rate limit: first request sets TTL, Nth request exceeds limit
- Username rate limit: extracts username from body, respects window
- `Retry-After` header set correctly

---

#### `test_logging.py` (`app/core/logging.py`)

**What to test**:
- JSON formatter produces valid JSON
- Request ID injected from ContextVar
- Severity mapping (level name to lowercase)
- Extra fields included at top level

---

## Integration Tests (`tests/integration/`)

### Characteristics
- **Slower**: Real database operations (seconds)
- **Real DB**: Async PostgreSQL connection (test database)
- **Mocked External Services**: Redis, JWT keys (but uses real PyJWT with mock keys)
- **HTTP Testing**: Uses `httpx.AsyncClient` with ASGI app directly (no network)
- **Fixtures**: Each test runs in transaction that's rolled back

### Test Database Setup

**`tests/conftest.py`** (general):
- `engine` fixture: Creates test engine with `NullPool`, drops and creates all tables, disposes after session
- `db` fixture: Creates session, yields to test, truncates all tables after (RESTART IDENTITY CASCADE)
- `override_get_db` fixture: Overrides FastAPI `get_db` to use test session

**`tests/integration/conftest.py`**:
- `override_engine`: Replace production `async_engine` in `app.db.session` with test engine (autouse)
- `patch_app_main`: Patch `key_pair`, `redis_client`, `async_engine` in `app.main` module so lifespan uses mocks (autouse)
- `admin_user`: Creates super user in DB before tests
- `admin_token`: Generates JWT signed with mock private key, roles=["admin"], permissions=["*"]
- `regular_user`: Creates non-super user
- `viewer_role`: Ensures 'viewer' role exists
- `client`: `httpx.AsyncClient` with ASGITransport

---

### Example Integration Tests

#### `test_auth_routes.py`

```python
@pytest.mark.asyncio
async def test_signup_creates_user_and_assigns_viewer_role(client, db, viewer_role):
    response = await client.post(
        "/api/v1/auth/signup",
        json={"username": "newuser", "password": "SecurePass123!", "email": "test@example.com"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "test@example.com"
    assert "id" in data

    # Verify user exists in DB
    from app.models.user import User
    user = await db.get(User, UUID(data["id"]))
    assert user is not None
    # Verify viewer role assigned (check user_roles table)
    ...

@pytest.mark.asyncio
async def test_login_sets_refresh_token_cookie(client, db, viewer_role):
    # Create user first via direct DB insert or signup
    ...

    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "newuser", "password": "SecurePass123!"}
    )
    assert response.status_code == 200
    assert "refresh_token" in response.cookies
    assert response.cookies["refresh_token"] is not None
```

---

#### `test_admin_routes.py`

Comprehensive tests for all admin endpoints (21 tests):

- `test_create_role_success`
- `test_create_role_duplicate_name_fails`
- `test_delete_role_success`
- `test_delete_system_role_forbidden`
- `test_delete_nonexistent_role_returns_404`
- `test_assign_permission_creates_permission_if_missing`
- `test_assign_permission_already_granted_409`
- `test_revoke_permission_not_found`
- `test_assign_role_to_user_success`
- `test_assign_role_to_user_already_assigned_409`
- `test_assign_role_to_nonexistent_user_404`
- `test_revoke_role_from_user_success`
- `test_revoke_role_from_user_not_assigned_404`
- `test_get_audit_logs_paginated`
- `test_admin_endpoints_require_super_user` (all admin endpoints return 403 for non-super)

**Example**:
```python
@pytest.mark.asyncio
async def test_assign_role_to_user_creates_audit_log(client, db, admin_token, regular_user, editor_role):
    response = await client.post(
        f"/api/v1/admin/users/{regular_user.id}/roles",
        json={"role_id": str(editor_role.id)},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == str(regular_user.id)
    assert data["role_id"] == str(editor_role.id)

    # Verify audit log entry
    from app.models.audit_log import AuditLog
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(1))
    log = result.scalar_one()
    assert log.action == "USER_ROLE_ASSIGNED"
    assert "user_id" in log.payload
```

---

#### `test_jwks_routes.py`

```python
@pytest.mark.asyncio
async def test_jwks_returns_expected_keys(client, mock_jwt):
    response = await client.get("/.well-known/jwks.json")
    assert response.status_code == 200
    data = response.json()
    assert "keys" in data
    assert len(data["keys"]) == 1
    key = data["keys"][0]
    assert key["kty"] == "RSA"
    assert key["use"] == "sig"
    assert "kid" in key
    assert "n" in key
    assert "e" in key
    assert key["e"] == "AQAB"  # 65537

@pytest.mark.asyncio
async def test_jwks_key_consistent_across_calls(client):
    response1 = await client.get("/.well-known/jwks.json")
    response2 = await client.get("/.well-known/jwks.json")
    assert response1.json() == response2.json()
```

---

## Running Tests

### All Tests
```bash
uv run pytest
```

### Unit Tests Only
```bash
uv run pytest tests/unit/ -v
```

### Integration Tests Only
```bash
uv run pytest tests/integration/ -v
```

### Single Test File
```bash
uv run pytest tests/unit/test_security.py -v
```

### Single Test Function
```bash
uv run pytest tests/unit/test_security.py::test_create_access_token_contains_roles -v
```

### With Coverage
```bash
uv run pytest --cov=app --cov-report=term-missing --cov-report=html
```

Output:
```
Name                     Stmts   Miss  Cover   Missing
------------------------------------------------------
app/core/security.py       50      0   100%
app/services/auth.py      150     10    93%   45-47, 88-90
...
TOTAL                     1200     50    96%
```

---

## Test Fixtures Reference

### `tests/conftest.py` (General)

- `engine` (session): Creates/drops test DB schema
- `db` (function): AsyncSession with cleanup
- `override_get_db` (function): Overrides FastAPI dependency
- `mock_redis` (session): Patches `redis_client` in multiple modules
- `mock_jwt` (session): Patches `RSAKeyPair` with mock keys

---

### `tests/integration/conftest.py` (Integration-specific)

- `override_engine` (session, autouse): Replaces production `async_engine`
- `patch_app_main` (session, autouse): Patches main app lifetime dependencies
- `admin_user` (function): Super user fixture
- `admin_token` (function): JWT for super user (using mock_jwt keys)
- `regular_user` (function): Normal user fixture
- `viewer_role` (function): Guarantees viewer role exists
- `client` (function): `httpx.AsyncClient` with app

---

## End-to-End Flow Tests

### Login → Access Protected → Refresh → Logout

```python
@pytest.mark.asyncio
async def test_full_auth_flow(client, db, viewer_role):
    # 1. Signup
    response = await client.post("/api/v1/auth/signup", json={
        "username": "e2euser",
        "password": "SecurePass123!"
    })
    assert response.status_code == 201
    user_id = response.json()["id"]

    # 2. Login
    response = await client.post("/api/v1/auth/login", json={
        "username": "e2euser",
        "password": "SecurePass123!"
    })
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    refresh_token = response.cookies["refresh_token"]

    # 3. Access protected endpoint
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == "e2euser"

    # 4. Refresh access token
    response = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    new_access_token = response.json()["access_token"]
    new_refresh_token = response.cookies["refresh_token"]
    assert new_access_token != access_token
    assert new_refresh_token != refresh_token

    # 5. Logout (old refresh token should be invalid)
    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}"},
        cookies={"refresh_token": refresh_token}
    )
    assert response.status_code == 204

    # 6. Verify old refresh token fails
    response = await client.post(
        "/api/v1/auth/refresh",
        cookies={"refresh_token": refresh_token}
    )
    assert response.status_code == 401
```

---

## Mocking External Services

### Redis Mock

In `tests/conftest.py`:
```python
@pytest.fixture(scope="session")
def mock_redis():
    redis_mock = AsyncMock()
    redis_mock.ping.return_value = True
    # ... other methods
    return redis_mock

@pytest.fixture(autouse=True)
def _patch_redis(mock_redis, mocker):
    mocker.patch("app.db.redis.redis_client", mock_redis)
    mocker.patch("app.core.rate_limit.redis_client", mock_redis)
    mocker.patch("app.services.auth_service.redis_client", mock_redis)
    mocker.patch("app.core.dependencies.redis_client", mock_redis)
```

All Redis operations return configured values or `None`.

---

### JWT Mock

`tests/conftest.py` creates real RSA keys with `cryptography` library and patches `RSAKeyPair` singleton:

```python
@pytest.fixture(scope="session")
def mock_jwt():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return MagicMock(private_key=private_key, public_key=public_key)

@pytest.fixture(autouse=True)
def _patch_jwt(mock_jwt, mocker):
    mocker.patch("app.core.keys.RSAKeyPair._instance", mock_jwt)
    mocker.patch("app.core.security.key_pair", mock_jwt)
    mocker.patch("app.core.dependencies.key_pair", mock_jwt)
```

**Note**: `jwt.encode` and `jwt.decode` from PyJWT are NOT mocked, so real cryptographic operations occur with mock keys. This tests actual JWT flow end-to-end within unit tests.

---

## Performance Testing (Optional)

Use `pytest-benchmark` or dedicated load testing tools:

```bash
# Install pytest-benchmark
uv add --dev pytest-benchmark

# Add benchmark tests
def test_login_performance(benchmark, client, db):
    async def login():
        await client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "testpass"
        })
    result = benchmark(login)
    assert result.stats.mean < 0.1  # <100ms
```

For full load testing, use `locust`, `k6`, or Cloud Load Testing.

---

## Troubleshooting Common Test Issues

### Event Loop Closed Errors
Ensure `pytest-asyncio` is installed and `asyncio_mode = "auto"` in `pyproject.toml`.

### Database Locks
Integration tests truncate tables after each test. If using multiple connections, ensure autocommit mode for TRUNCATE. Current implementation uses RESTART IDENTITY CASCADE, which requires no open transactions.

### Mock Redis Not Applied
Check patch targets are correct module paths; order of fixture application matters. Use `mocker.patch.object` if needed.

### JWT Signature Invalid
Make sure mock JWT fixture uses real RSA keys, not strings. `jwt.encode/decode` require actual ` cryptography ` key objects.

---

## References

- Test files: `tests/unit/`, `tests/integration/`
- Fixtures: `tests/conftest.py`, `tests/integration/conftest.py`
- Services: `app/services/`
- API: `app/api/v1/`
- Core: `app/core/`
