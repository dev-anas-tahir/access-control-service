# AGENTS.md — Access Control Service

## Project Overview

This is a standalone **Access Control Service** microservice built with FastAPI (Python 3.13).
It handles authentication (JWT via RS256), authorization (RBAC), and user/session management.
It is part of a larger platform migrated from Django and deployed on GCP.

<!-- TODO: Add 1-2 sentences describing the broader platform this service belongs to, e.g. "This service is consumed by an edutech platform that manages courses, students, and instructors." -->

---

## Tech Stack

| Layer            | Technology                                      |
|------------------|-------------------------------------------------|
| Framework        | FastAPI (Python 3.13)                           |
| ORM              | SQLAlchemy (async, 2.x style)                   |
| Migrations       | Alembic (async)                                 |
| Validation       | Pydantic v2                                     |
| Auth             | PyJWT + cryptography (RS256, RSA key pairs)     |
| Cache / Sessions | GCP Memorystore (Redis) via `redis.asyncio`     |
| Messaging        | GCP Pub/Sub                                     |
| Database         | <!-- TODO: PostgreSQL version, e.g. PostgreSQL 15 via Cloud SQL --> |
| Package Manager  | uv                                              |
| Testing          | pytest + pytest-asyncio + httpx (AsyncClient)   |

---

## Project Structure
```
app/
├── core/
│   ├── config.py          # Settings via pydantic-settings
│   ├── security.py        # RSA key loading, JWT encode/decode, bcrypt hashing
│   └── dependencies.py    # FastAPI dependency injection (DB, Redis, current user)
├── db/
│   ├── base.py            # SQLAlchemy async engine + session factory
│   ├── mixins.py          # TimestampMixin, SoftDeleteMixin
│   └── models/            # SQLAlchemy ORM models
├── schemas/               # Pydantic v2 request/response schemas
├── services/
│   ├── auth_service.py    # Login, token issuance, refresh, lazy bcrypt migration
│   └── rbac_service.py    # Role/permission assignment and checks
├── routes/
│   ├── auth.py            # /auth/* endpoints
│   ├── jwks.py            # /.well-known/jwks.json
│   └── admin.py           # /admin/* endpoints (roles, permissions, user management)
├── events/
│   └── pubsub.py          # GCP Pub/Sub publisher setup
└── main.py                # App factory, lifespan, router registration

tests/
├── conftest.py            # Shared fixtures: async DB session, Redis mock, test client
├── unit/                  # Pure logic tests (no DB/network)
│   ├── test_security.py
│   └── test_rbac_service.py
└── integration/           # Tests against a real async DB (test database)
    ├── test_auth_routes.py
    └── test_admin_routes.py

keys/
├── private.pem            # RSA private key — NEVER commit this
└── public.pem             # RSA public key
```

<!-- TODO: If your actual directory layout differs (e.g. events/ is named differently, or keys are loaded from GCP Secret Manager), update the tree above to match exactly. -->

---

## Setup Commands
```bash
# Install dependencies
uv sync

# Run dev server
uvicorn app.main:app --reload --port 8000

# Run all tests
uv run pytest

# Run only unit tests
uv run pytest tests/unit/ -v

# Run only integration tests
uv run pytest tests/integration/ -v

# Run with coverage
uv run pytest --cov=app --cov-report=term-missing

# Apply migrations
uv run alembic upgrade head

# Generate a new migration
uv run alembic revision --autogenerate -m "describe_change"

# Lint and format
ruff check .
ruff format .
```

<!-- TODO: If you have a Makefile or shell scripts wrapping these, add the shorthand commands here (e.g. `make test`, `make migrate`). -->

---

## Environment Variables

All settings are loaded via `app/core/config.py` using `pydantic-settings`.
Never hardcode secrets. Load from `.env` locally and from GCP Secret Manager in production.

Required variables:
```
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
RSA_PRIVATE_KEY_PATH=keys/private.pem
RSA_PUBLIC_KEY_PATH=keys/public.pem
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
GCP_PROJECT_ID=...
PUBSUB_TOPIC_ACTIVITY=...
```

<!-- TODO: Add any additional env vars your config.py defines, e.g. ENVIRONMENT=development|production, LOG_LEVEL, ALLOWED_ORIGINS, etc. -->

---

## Code Conventions

### General
- Python 3.13. Use modern type hints: `list[str]`, `dict[str, int]`, `X | None` (not `Optional[X]`).
- All functions and methods must have full type annotations, including return types.
- Never use mutable default arguments (e.g. `def f(x: list = [])` is forbidden).
- Async-first: all route handlers, service methods, and DB calls must be `async def`.
- Use `await` on every coroutine. Missing `await` is a common bug — always double-check.

### SQLAlchemy
- Use SQLAlchemy 2.x async style: `async with session` and `await session.execute(...)`.
- Use `server_default` for DB-generated defaults (e.g. timestamps), not `default`.
- Use `default` only for Python-side defaults (e.g. `default=uuid.uuid4`).
- All models inherit `TimestampMixin` and `SoftDeleteMixin` where appropriate.
- Never use `session.commit()` inside service functions — commit is the caller's responsibility unless explicitly noted.

### Pydantic v2
- Use `model_config = ConfigDict(...)` instead of inner `class Config`.
- Use `model_validator` and `field_validator` with `@classmethod`.
- Separate schemas for input and output: e.g. `UserCreate`, `UserRead`, never reuse the same model.
- Never expose password hashes or internal fields in response schemas.

### Authentication & Security
- Tokens are RS256-signed JWTs. Use `PyJWT` with the `cryptography` backend. Do NOT use `python-jose`.
- Access tokens: short-lived (configurable, default 15 min).
- Refresh tokens: 7-day expiry, stored in httpOnly cookies, JTI tracked in Redis for revocation.
- Passwords are hashed with bcrypt via `passlib`. Use `needs_update()` for lazy migration from Django's pbkdf2.
- JTI (JWT ID) must be checked against Redis on every protected request to support revocation.

### Routing
- All routes use `/api/v1` prefix.
- Route handlers are thin: validate input, call a service, return a response schema. No business logic in routes.
- Use `status_code` explicitly on all route decorators.
- Always set `response_model` on route decorators.

### Error Handling
- Raise `HTTPException` with explicit status codes and detail messages from route handlers.
- Service layer raises domain-specific exceptions (e.g. `InvalidCredentialsError`); route layer maps them to `HTTPException`.
- Never leak internal error details (stack traces, DB errors) to API responses.

---

## Testing Conventions

### General Rules
- Always add tests when adding or modifying a feature, even if not asked.
- All tests must pass before a task is considered complete.
- Run `pytest` before finishing any task.

### Unit Tests (`tests/unit/`)
- Test pure logic only: JWT encoding/decoding, password hashing, permission checks, schema validation.
- No real DB, Redis, or HTTP calls. Mock all external dependencies.
- Fast — should complete in under 1 second.

### Integration Tests (`tests/integration/`)
- Use `httpx.AsyncClient` with the FastAPI `app` directly (no running server needed).
- Use a separate test database (configured via `TEST_DATABASE_URL` env var or conftest override).
- Each test should be isolated: set up and tear down its own data.
- Do NOT share mutable state between tests.
- Mock GCP Pub/Sub in integration tests — do not publish real events.

### Fixtures (`tests/conftest.py`)
- Provide: async DB session, overridden `get_db` dependency, `AsyncClient`, Redis mock.
- Use `pytest-asyncio` with `asyncio_mode = "auto"` in `pytest.ini` or `pyproject.toml`.

<!-- TODO: If you have a specific test database name or a docker-compose setup for tests, document it here. -->

---

## Boundaries & Constraints

These actions require **explicit confirmation before proceeding**:

- Modifying Alembic migration files or generating new ones.
- Changing SQLAlchemy model definitions (schema changes).
- Changing the JWT signing algorithm or key loading logic.
- Modifying `app/core/config.py` settings definitions.
- Deleting or renaming existing API routes (breaking change).

These actions are **forbidden**:

- Committing `.env` files, `private.pem`, or any secrets.
- Using `python-jose` — always use `PyJWT` with `cryptography`.
- Using synchronous SQLAlchemy calls inside async context.
- Adding `print()` statements for debugging — use the logger.
- Hardcoding any configuration values that belong in `.env`.

---

## GCP Infrastructure Notes

- **Database**: Cloud SQL (PostgreSQL) — async connection via `asyncpg`.
- **Cache**: Memorystore (Redis) — used for refresh token JTI storage and revocation.
- **Messaging**: Pub/Sub — used to publish activity events asynchronously to the activity tracker service.
- **Secrets**: GCP Secret Manager for production secrets (RSA keys, DB credentials).

<!-- TODO: Add your GCP project ID, region, and Cloud SQL instance name here so the agent has full deployment context. Example: "Project: my-project-id, Region: us-central1, SQL Instance: access-control-db" -->

---

## Common Bugs to Avoid

These are recurring issues in this codebase — always check for them:

1. **Missing `await`** on async DB calls or Redis operations.
2. **`default` vs `server_default`** in SQLAlchemy columns — use `server_default` for DB-generated values.
3. **Wrong JWT library** — never import from `jose`, always from `jwt` (`PyJWT`).
4. **Mutable default arguments** in function signatures.
5. **Exposing password hashes** in Pydantic response schemas.
6. **Not checking JTI revocation** in the token validation dependency.
