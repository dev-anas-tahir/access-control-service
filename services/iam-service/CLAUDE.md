# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Run from `services/iam-service/` unless stated otherwise.

```bash
# Dev server
just runserver                          # uvicorn app.main:app --reload --port 8000

# Migrations
just makemigrations "describe_change"   # alembic revision --autogenerate -m "..."
just migrate                            # alembic upgrade head

# Tests
uv run pytest --cov=app --cov-report=term-missing   # all tests with coverage
uv run pytest tests/unit/ -v                         # unit tests only (no DB needed)
uv run pytest tests/integration/ -v                  # integration tests (needs TEST_DATABASE_URL)
uv run pytest tests/unit/rbac/test_create_role_use_case.py -v   # single file

# Lint / format
ruff check app tests
ruff format app tests
```

**First-time setup:**
```bash
mkdir -p keys
openssl genrsa -out keys/private_key.pem 2048
openssl rsa -in keys/private_key.pem -pubout -out keys/public_key.pem
uv run alembic upgrade head
```

## Architecture

### Hexagonal — Three Bounded Contexts

Each of `auth/`, `rbac/`, `audit/` is independently layered:

```
<context>/
├── domain/         # Pure Python: dataclasses, Protocol ports, exceptions
├── application/    # Use cases + DTOs; import only from domain/
└── infrastructure/
    ├── composition.py        # FastAPI Depends wiring — only place concrete types are assembled
    ├── http/routes.py        # Thin handlers: validate → call use case → return schema
    ├── http/exception_mapper.py  # Maps domain exceptions to HTTPException
    ├── orm/                  # SQLAlchemy ORM models
    └── repositories/         # SqlAlchemy implementations of domain ports
```

**The domain layer must never import from FastAPI, SQLAlchemy, Redis, or PyJWT.**

### Exception mapping pattern

Domain exceptions never become `HTTPException` inside routes. Each bounded context registers its own handlers on the FastAPI app via `register_<context>_exception_handlers(app)` in `exception_mapper.py`. Routes just call use cases and let exceptions propagate.

### Shared modules
- `app/shared/domain/` — canonical `User`, `Role`, `Permission`, `AuditLog` entities; `Email` and `ScopeKey` value objects; `DomainEvent` base class
- `app/shared/infrastructure/` — ORM mixins (`UUIDPrimaryKeyMixin`, `TimestampMixin`, `SoftDeleteMixin`), `RSAKeyPair` singleton loaded once at startup, `BcryptPasswordHasher`, JWT issuer/verifier, Redis client, rate limiting
- `app/core/` — `RequestResponseMiddleware` (request-ID injection, structured logging)
- `app/config.py` — `Settings(BaseSettings)` singleton; all config via env vars

### Key entities
| Entity | Fields |
|--------|--------|
| `User` | `id`, `username`, `password_hash`, `is_active`, `is_super_user`, `roles: list[Role]`, `email\|None`, `organization_id\|None` |
| `Role` | `id`, `name`, `description`, `is_system`, `created_by`, `is_deleted`, `permissions: list[Permission]` |
| `Permission` | `id`, `scope_key: ScopeKey` (`resource:action`) |
| `AuditLog` | `id`, `actor_id`, `action`, `entity_type`, `entity_id`, `payload: dict` |

### Auth flow
1. `POST /api/v1/auth/login` — verify password, build `TokenClaims` (`sub`, `username`, `roles`, `permissions`, `is_super_user`, `jti`), issue RS256 JWT access token + refresh token stored in Redis
2. `POST /api/v1/auth/refresh` — consume refresh token from httpOnly cookie, check JTI revocation set, issue new pair
3. `POST /api/v1/auth/logout` — revoke JTI, delete refresh token from Redis

Password hashing uses `passlib` with schemes `["bcrypt", "django_pbkdf2_sha256"]` — auto-migrates Django hashes to bcrypt on first login via `needs_update()`.

Every protected request checks JTI against `RedisRevocationStore` — missing this check means logout doesn't invalidate tokens.

### RBAC → Audit decoupling via Domain Events
RBAC use cases call `uow.add_event(RoleCreated(...))`. After `uow.commit()`, the Unit of Work dispatches collected events to `SqlAlchemyAuditLogger` — the two contexts never import each other.

Domain events: `RoleCreated`, `RoleDeleted`, `PermissionGranted`, `PermissionRevoked`, `UserRoleAssigned`, `UserRoleRevoked`. Each implements `to_audit_payload() -> dict`.

### API surface
| Prefix | Context |
|--------|---------|
| `/api/v1/auth` | auth — signup, login, refresh, logout, /me |
| `/api/v1/admin` | rbac — roles, permissions, user-role assignments (super user only) |
| `/api/v1/audit` | audit — paginated log read |
| `/.well-known/jwks.json` | JWKS — public key for downstream JWT verification |

All admin routes are guarded by `require_super_user` dependency (checks `is_super_user` claim in JWT).

### Rate limiting
- `rate_limit_by_ip`: 20 req/min — applied to all auth routes
- `rate_limit_by_username`: 5 failed attempts / 5 min — applied to login only

### ORM association tables
- `user_roles(user_id, role_id, assigned_by, assigned_at)`
- `role_permissions(role_id, permission_id, granted_by, granted_at)`

SQLAlchemy queries eagerly load `User.roles → Role.permissions` via `selectinload`.

## Tests

**Unit tests** (`tests/unit/`): use `FakeRbacUnitOfWork` and in-memory fakes from `tests/unit/rbac/fakes.py` — no DB, no network, no real async.

**Integration tests** (`tests/integration/`): real async PostgreSQL via `TEST_DATABASE_URL`, `httpx.AsyncClient`, Pub/Sub mocked.

**Shared fixtures** (`tests/conftest.py`):
- `engine` (session-scope) — creates all tables once; skips if `TEST_DATABASE_URL` unset
- `db` (function-scope) — fresh `AsyncSession`, truncates all tables after each test
- `override_get_db` — overrides `get_db` FastAPI dependency with test session
- `mock_redis` (session-scope) — `AsyncMock` patched into redis, rate_limit, and auth_composition modules
- `mock_jwt` (session-scope) — in-memory 2048-bit RSA pair injected into `RSAKeyPair` singleton

## Environment Variables

See `.env.example`. Required:
- `DATABASE_URL` / `TEST_DATABASE_URL` — asyncpg PostgreSQL DSN
- `REDIS_URL`
- `PRIVATE_KEY_PATH` / `PUBLIC_KEY_PATH` (default: `keys/private_key.pem` / `keys/public_key.pem`)
- `GCP_PROJECT_ID` / `PUBSUB_TOPIC_ID`
- `JWT_ISSUER` (default: `access-control-service`), `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 15), `REFRESH_TOKEN_EXPIRE_DAYS` (default: 7)

## Common pitfalls

- **Missing `await`** on async DB/Redis calls — silent failures or type errors at runtime
- **`default` vs `server_default`** — use `server_default` for DB-generated values (timestamps), `default=uuid.uuid4` for Python-side
- **JTI revocation** — every protected route must pass the token through `RedisRevocationStore`; omitting it means logout is a no-op
- **Wrong JWT library** — always `import jwt` (PyJWT); never `from jose import jwt`
- **Exposing `password_hash`** in Pydantic response schemas

## Docs

Full HTTP request/response schemas: `docs/03-api-contracts.md`. JWT/Redis/bcrypt security details: `docs/05-security-architecture.md`. Sequence diagrams: `docs/09-sequence-diagrams.md`.
