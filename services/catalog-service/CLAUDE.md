# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Run from `services/catalog-service/` unless stated otherwise.

```bash
# Dev server
just runserver                          # uvicorn app.main:app --reload --port 8001

# Migrations
just makemigrations "describe_change"   # alembic revision --autogenerate -m "..."
just migrate                            # alembic upgrade head

# Tests
uv run pytest --cov=app --cov-report=term-missing
uv run pytest tests/unit/ -v                         # no DB needed
uv run pytest tests/integration/ -v                  # needs TEST_DATABASE_URL
uv run pytest tests/unit/catalog/test_create_product_use_case.py -v

# Lint / format
ruff check app tests
ruff format app tests
```

## Architecture

### Hexagonal — Two Bounded Contexts

`app/catalog/` and `app/inventory/` are independently layered:

```
<context>/
├── domain/         # Pure Python: dataclasses, Protocol ports, exceptions, events
├── application/    # Use cases + DTOs; import only from domain/
└── infrastructure/
    ├── composition.py            # FastAPI Depends wiring
    ├── http/routes.py            # Thin handlers only
    ├── http/exception_mapper.py  # Maps domain exceptions → HTTPException
    ├── orm/                      # SQLAlchemy ORM models
    └── repositories/             # SqlAlchemy implementations + ORM↔domain mappers
```

Each context's `infrastructure/http/exception_mapper.py` registers `@app.exception_handler` handlers — domain exceptions are never caught inside routes.

### Shared modules
- `app/shared/infrastructure/db/` — async engine, session factory, `Base` (all ORM models inherit from it)
- `app/shared/infrastructure/events/pubsub_publisher.py` — `publish_event(event_type, payload)` — called by both UoW implementations after commit
- `app/shared/infrastructure/http/jwks.py` — `JwksClient` singleton; fetches and caches the RS256 public key from iam-service at startup

### Key entities

**catalog context:**
| Entity | Key fields |
|--------|-----------|
| `Product` | `id`, `name`, `description`, `category_id`, `status: ProductStatus`, `created_by`, `variants: list[ProductVariant]` |
| `ProductVariant` | `id`, `product_id`, `sku`, `price`, `attributes: dict`, `is_active` |
| `Category` | `id`, `name`, `slug`, `parent_id\|None` |

**inventory context:**
| Entity | Key fields |
|--------|-----------|
| `Inventory` | `id`, `variant_id`, `quantity_on_hand`, `quantity_reserved` |

`Inventory.available` = `on_hand − reserved`. Methods: `reserve(qty)`, `release(qty)`, `restock(qty)`, `commit_reservation(qty)`.

`Product.activate()` returns `True` only if the transition was `inactive → active` — the use case uses this return value to decide whether to emit `ProductPublished`.

### Domain events

Events are collected via `uow.add_event(...)` and published to GCP Pub/Sub after `uow.commit()` via `pubsub_publisher.publish_event`. Events are never published on rollback.

**catalog events** (`app/catalog/domain/events.py`):
- `ProductPublished` — fired only on `inactive → active` transition; carries `product_id`, `name`, `category_id`
- `ProductPriceChanged` — fired when a variant price changes on an active product; carries `product_id`, `variant_id`, `sku`, `old_price`, `new_price`

**inventory events** (`app/inventory/domain/events.py`):
- `InventoryRestocked` — fired when `restock()` is called; carries `variant_id`, `quantity_added`, `quantity_on_hand`
- `InventoryDepleted` — fired when stock reaches zero after a committed reservation; carries `variant_id`

All events implement `to_pubsub_payload() -> dict` and expose `event_type` (class name).

### JWT authentication

- **Reads** — public, no token required
- **Mutations** — `require_catalog_write` dependency in `app/catalog/infrastructure/http/dependencies.py` verifies the RS256 JWT and checks for the `catalog:write` permission claim
- `JwksClient` fetches `GET /.well-known/jwks.json` from iam-service (configured via `IAM_JWKS_URL`) at startup via `app.lifespan`. In tests, `jwks_client._public_key` is patched with a `MagicMock` to bypass verification.
- JWT payload extracted via `payload["sub"]` for `actor_id` in all write routes

### API surface

| Prefix | Description |
|--------|-------------|
| `GET /api/v1/catalog/products` | list active products (public) |
| `GET /api/v1/catalog/products/{id}` | get product with variants (public) |
| `POST /api/v1/catalog/products` | create product — requires `catalog:write` |
| `PATCH /api/v1/catalog/products/{id}` | update product metadata |
| `PATCH /api/v1/catalog/products/{id}/status` | activate or deactivate |
| `POST /api/v1/catalog/products/{id}/variants` | add variant |
| `PATCH /api/v1/catalog/variants/{id}` | update variant price/attributes |
| `DELETE /api/v1/catalog/variants/{id}` | soft-delete variant |
| `GET /api/v1/catalog/categories` | list all categories (public) |
| `POST /api/v1/catalog/categories` | create category |
| `GET /api/v1/inventory/variants/{id}` | get stock levels (public) |
| `POST /api/v1/inventory/variants/{id}/restock` | add stock |
| `POST /api/v1/inventory/variants/{id}/reserve` | reserve stock for checkout |
| `POST /api/v1/inventory/variants/{id}/release` | release a reservation |

## Tests

**Unit tests** (`tests/unit/`): use in-memory fakes from `tests/unit/catalog/fakes.py` and `tests/unit/inventory/fakes.py` — `FakeCatalogUnitOfWork`, `FakeProductRepository`, `FakeCategoryRepository`, `FakeInventoryUnitOfWork`. Check `uow.emitted_events` to assert Pub/Sub events were queued.

**Integration tests** (`tests/integration/`): real async PostgreSQL, `httpx.AsyncClient` via `ASGITransport`. `jwks_client._public_key` is patched to a `MagicMock` so JWT verification is bypassed.

**Shared fixtures** (`tests/conftest.py`):
- `engine` (session-scope) — creates all tables; skips if `TEST_DATABASE_URL` unset
- `create_tables` (session-scope) — `Base.metadata.create_all` / `drop_all`
- `db` (function-scope) — `AsyncSession` with rollback + table truncation after each test
- `client` (function-scope) — `httpx.AsyncClient` with JWKS patched

## Environment Variables

See `.env.example`. Required:
- `DATABASE_URL` / `TEST_DATABASE_URL` — asyncpg PostgreSQL DSN
- `IAM_JWKS_URL` — e.g. `http://iam-service:8000/.well-known/jwks.json`
- `GCP_PROJECT_ID` / `PUBSUB_TOPIC_ID`

## Common pitfalls

- **`ProductPublished` fires only on `inactive → active`** — `SetProductStatusUseCase` checks `product.activate()` return value; emitting unconditionally is wrong
- **`quantity_reserved` never exceeds `quantity_on_hand`** — `Inventory.reserve()` raises `ValueError` if violated; do not bypass with direct field assignment
- **Hard deletes are forbidden** — use `Product.status = inactive` or `ProductVariant.is_active = False`; no `DELETE` on the products table
- **`sku` must be globally unique** — always call `uow.products.sku_exists(sku)` before `add_variant`
- **JWKS loaded at startup** — if `iam-service` is unreachable at boot the app will fail; in tests always patch `jwks_client._public_key`
