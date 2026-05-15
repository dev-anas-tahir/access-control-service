# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the **Shop-Monorepo** — a `uv` workspace containing four microservices and shared packages for an ecommerce platform. The primary service is `services/iam-service`, a full-featured IAM/RBAC system deployed to GCP.

**Workspace members**: `services/iam-service`, `services/catalog-service`, `services/order-service`, `services/notification-service`, `packages/shared`

## Commands

All commands assume you are inside `services/iam-service/` unless stated otherwise.

### Setup
```bash
# From repo root — installs all workspace dependencies
uv sync

# Generate RSA keys (one-time)
mkdir -p keys
openssl genrsa -out keys/private_key.pem 2048
openssl rsa -in keys/private_key.pem -pubout -out keys/public_key.pem

# Apply migrations
uv run alembic upgrade head
```

### Running
```bash
uvicorn app.main:app --reload --port 8000
# or
just runserver
```

### Testing
```bash
# All tests with coverage
uv run pytest --cov=app --cov-report=term-missing

# Unit tests only (fast, no DB)
uv run pytest tests/unit/ -v

# Integration tests (requires real async DB)
uv run pytest tests/integration/ -v

# Single test file
uv run pytest tests/unit/rbac/test_create_role_use_case.py -v
```

### Linting & Formatting
```bash
ruff check app tests
ruff format app tests
```

### Docker (from repo root)
```bash
docker-compose up
# PostgreSQL :5432, Redis :6379, IAM :8000, Catalog :8001, Order :8002, Notification :8003, Pub/Sub emulator :8085
```

### Migrations
```bash
just makemigrations "describe_change"   # alembic revision --autogenerate -m "..."
just migrate                             # alembic upgrade head
```

## Architecture

### Hexagonal (Ports & Adapters) with Three Bounded Contexts

`services/iam-service/app/` has three bounded contexts — `auth/`, `rbac/`, `audit/` — each strictly layered:

```
<context>/
├── domain/         # Pure Python: entities, value objects, ports (Protocol), exceptions
├── application/    # Use cases + DTOs; depend only on domain ports
└── infrastructure/ # Adapters: SQLAlchemy repos, Redis, FastAPI routes, JWT, Pub/Sub
```

**The domain layer has zero imports from FastAPI, SQLAlchemy, Redis, or PyJWT.** Use cases receive concrete implementations injected at startup via `composition.py` files.

### Cross-cutting modules
- `app/shared/` — `User`, `Role`, `Permission` entities and value objects shared across bounded contexts
- `app/core/` — Logging, middleware, request context (correlation IDs)
- `app/config.py` — `pydantic-settings` settings class; all config via env vars
- `app/main.py` — App factory, lifespan startup/shutdown, router registration

### Authentication Flow
- RS256 JWTs with RSA key pairs (paths from `PRIVATE_KEY_PATH` / `PUBLIC_KEY_PATH`)
- Access tokens: short-lived (default 15 min)
- Refresh tokens: 7-day expiry stored in Redis, delivered via httpOnly cookies, JTI revocation prevents reuse
- bcrypt password hashing with lazy migration path from Django's PBKDF2

### RBAC & Audit Decoupling via Domain Events
RBAC use cases emit domain events (`RoleCreated`, `PermissionGranted`, `UserRoleAssigned`, etc.). The Unit of Work collects events post-commit and dispatches them to the audit logger — keeping `rbac/` and `audit/` fully decoupled. All RBAC mutation operations require the `is_superuser` flag.

### Database
- SQLAlchemy 2.x async ORM with `asyncpg` driver
- Alembic migrations in `services/iam-service/alembic/`
- `SoftDeleteMixin` for soft deletes, `UUIDMixin` for primary keys
- Pool: `pool_size=10`, `max_overflow=20` (configurable via env)

### Caching (Redis)
- Refresh token storage and JTI revocation set
- Rate limiting keyed by IP and username

## Key Environment Variables

See `.env.example` in `services/iam-service/`. Required at minimum:
- `DATABASE_URL`, `TEST_DATABASE_URL`
- `REDIS_URL`
- `PRIVATE_KEY_PATH`, `PUBLIC_KEY_PATH`
- `JWT_ISSUER`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`
- `GCP_PROJECT_ID`, `PUBSUB_TOPIC_ID` (for Pub/Sub event publishing)

## Testing Conventions

- **Unit tests** (`tests/unit/`): pure logic, all external dependencies mocked via `unittest.mock` or `pytest` fixtures — no DB or network
- **Integration tests** (`tests/integration/`): real async PostgreSQL, `httpx.AsyncClient` against the running app, Pub/Sub mocked
- Shared fixtures live in `tests/conftest.py`: async engine, DB session override, mock Redis client, in-memory RSA key pair for JWT

## Code Conventions

- Python 3.13; modern type hints (`list[str]`, `X | None`, no `Optional`)
- Async-first — all route handlers, use cases, and repository methods are `async def`
- Google-style docstrings
- Ruff enforced: line-length 88, rules E, F, I

## Deployment

CI/CD via `.github/workflows/iam-service.yml`:
1. **Lint** — `ruff check`
2. **Test** — pytest against ephemeral PostgreSQL 17 + Redis 7 containers
3. **Deploy** (on `main`) — builds Docker image, pushes to GCP Artifact Registry, deploys to Cloud Run

Target infra: GCP Cloud SQL (PostgreSQL 17), GCP Memorystore (Redis), GCP Cloud Run, GCP Pub/Sub.

## Further Reading

Architecture decision records and diagrams are in `services/iam-service/docs/` (00-executive-summary through 08-deployment-operations).
