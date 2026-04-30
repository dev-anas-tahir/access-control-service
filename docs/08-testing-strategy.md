# Testing Strategy

## Test Structure

```
tests/
├── conftest.py                      # Shared fixtures (DB engine, async client setup)
├── unit/
│   ├── auth/
│   │   ├── fakes.py                 # In-memory fakes for all auth ports
│   │   ├── test_signup_use_case.py
│   │   ├── test_login_use_case.py
│   │   ├── test_refresh_token_use_case.py
│   │   └── test_logout_use_case.py
│   ├── rbac/
│   │   ├── fakes.py                 # In-memory fakes for all RBAC ports
│   │   ├── test_create_role_use_case.py
│   │   ├── test_delete_role_use_case.py
│   │   ├── test_assign_permission_use_case.py
│   │   ├── test_revoke_permission_use_case.py
│   │   ├── test_assign_role_to_user_use_case.py
│   │   └── test_revoke_role_from_user_use_case.py
│   ├── audit/
│   │   └── test_get_audit_logs_use_case.py
│   ├── shared/
│   │   ├── test_email_value.py
│   │   ├── test_scope_key_value.py
│   │   ├── test_role_entity.py
│   │   └── test_user_entity.py
│   ├── test_dependencies.py         # get_current_user, require_super_user
│   ├── test_rate_limit.py
│   └── test_logging.py
└── integration/
    ├── conftest.py                  # DB override, admin token, httpx client
    ├── test_auth_routes.py
    ├── test_admin_routes.py
    └── test_jwks_routes.py
```

---

## Unit Tests (`tests/unit/`)

**Characteristics**: no DB, no Redis, no FastAPI, sub-100ms total. Use in-memory fakes, never mocks.

### Fakes pattern

Each bounded context has a `fakes.py` with:
- In-memory repository implementations
- `FakeUnitOfWork` that tracks `committed`, `emitted_events`, etc.
- Entity factory helpers (`make_role()`, `make_user()`, etc.)

**Example** (`tests/unit/rbac/fakes.py`):
```python
class FakeRbacUnitOfWork:
    def __init__(self, roles=None, permissions=None, ...):
        self.roles = roles or FakeRoleRepository()
        self.permissions = permissions or FakePermissionRepository()
        self.assignments = FakeAssignmentRepository()
        self.committed = False
        self._pending_events: list[DomainEvent] = []
        self.emitted_events: list[DomainEvent] = []

    async def commit(self) -> None:
        self.committed = True
        self.emitted_events.extend(self._pending_events)
        self._pending_events.clear()

    def add_event(self, event: DomainEvent) -> None:
        self._pending_events.append(event)
```

### Use case tests

Use cases receive a pre-built fake UoW; assertions check domain state and emitted events:

```python
async def test_create_role_emits_domain_event():
    uow = FakeRbacUnitOfWork()
    use_case = CreateRoleUseCase(uow_factory=lambda: uow)

    await use_case.execute(CreateRoleInput(name="editor", actor_id=uuid4()))

    assert uow.committed is True
    events = uow.emitted_events
    assert len(events) == 1
    assert isinstance(events[0], RoleCreated)
    assert events[0].name == "editor"
```

### Domain / value object tests

Test invariants directly on dataclasses — no fakes needed:

```python
def test_scope_key_parse_round_trip():
    sk = ScopeKey.parse("users:read")
    assert sk.resource == "users"
    assert sk.action == "read"
    assert sk.key == "users:read"

def test_system_role_is_not_deletable():
    role = Role(id=uuid4(), name="viewer", is_system=True, ...)
    with pytest.raises(SystemRoleProtectedError):
        role.assert_deletable()
```

---

## Integration Tests (`tests/integration/`)

**Characteristics**: real async PostgreSQL, mocked Redis (via `unittest.mock`), real PyJWT with test RSA keys. Uses `httpx.AsyncClient` against the ASGI app — no running server.

### Key fixtures (`tests/integration/conftest.py`)

| Fixture | Scope | Purpose |
|---------|-------|---------|
| `engine` | session | Creates test DB schema (`Base.metadata.create_all`), drops after |
| `override_session_factory` | session, autouse | Patches `async_session_factory` in all infrastructure modules with test factory |
| `mock_redis` | session | `AsyncMock` for all Redis operations |
| `admin_token` | function | Real JWT signed with test RSA key, `is_super_user=True` |
| `viewer_role` | function | Seeds 'viewer' role via direct DB insert |
| `client` | function | `httpx.AsyncClient(app=app, base_url="http://test")` |

### Example integration test

```python
async def test_signup_assigns_viewer_role(client, viewer_role):
    response = await client.post("/api/v1/auth/signup", json={
        "username": "alice", "password": "Secret1!", "email": "alice@example.com"
    })
    assert response.status_code == 201
    assert response.json()["username"] == "alice"

async def test_create_role_requires_super_user(client):
    response = await client.post(
        "/api/v1/admin/roles",
        json={"name": "editor"},
        headers={"Authorization": "Bearer unprivileged_token"},
    )
    assert response.status_code == 401
```

---

## Running Tests

```bash
# All tests
uv run pytest

# Unit tests only (fast, no DB)
uv run pytest tests/unit/ -v

# Integration tests only
uv run pytest tests/integration/ -v

# With coverage
uv run pytest --cov=app --cov-report=term-missing
```

**Configuration** (`pyproject.toml`):
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

No `@pytest.mark.asyncio` needed on individual tests.

---

## Architecture Invariant Checks

After any change, verify no layer leaks:
```bash
# Must return nothing — domain and application layers must stay framework-free
grep -r "from sqlalchemy" app/auth/domain/ app/auth/application/
grep -r "from sqlalchemy" app/rbac/domain/ app/rbac/application/
grep -r "from fastapi"    app/auth/domain/ app/auth/application/
grep -r "from fastapi"    app/rbac/domain/ app/rbac/application/
grep -r "redis"           app/auth/domain/ app/auth/application/
grep -r "redis"           app/rbac/domain/ app/rbac/application/
```
