# Component Details

## Bounded Contexts

The service is divided into three bounded contexts. Each owns its `domain/`, `application/`, and `infrastructure/` subtree.

---

## Auth Context (`app/auth/`)

Handles signup, login, token refresh, and logout.

### Domain ports (`app/auth/domain/ports/`)

| Port | Methods |
|------|---------|
| `UserRepository` | `find_by_username`, `find_by_email`, `find_by_id`, `add`, `update` |
| `RoleRepository` | `find_by_name` |
| `RefreshTokenStore` | `put(token, user_id, ttl)`, `get(token)`, `delete(token)` |
| `RevocationStore` | `revoke(jti, ttl)`, `is_revoked(jti)` |
| `PasswordHasher` | `hash`, `verify`, `needs_rehash` |
| `TokenIssuer` | `issue(claims) -> str` |
| `TokenVerifier` | `verify(token) -> TokenPayload` |
| `AuthUnitOfWork` | async context manager, `commit`, `rollback`, `.users`, `.roles` |

### Use cases (`app/auth/application/use_cases/`)

| Use Case | What it does |
|----------|-------------|
| `SignupUseCase` | Uniqueness check → hash password → create User → assign viewer role → commit |
| `LoginUseCase` | Verify credentials → optional lazy bcrypt rehash → issue tokens → store refresh token |
| `RefreshTokenUseCase` | Look up refresh token in Redis → load user → rotate tokens |
| `LogoutUseCase` | Delete refresh token → revoke JTI with remaining TTL |

All use cases receive dependencies via constructor injection. Zero imports from `infrastructure/`.

### Infrastructure adapters (`app/auth/infrastructure/`)

| Adapter | Description |
|---------|-------------|
| `SqlAlchemyAuthUnitOfWork` | Opens `AsyncSession`, builds repos, commits/rolls back |
| `SqlAlchemyUserRepository` | Eager-loads `User → roles → permissions` via `selectinload` |
| `SqlAlchemyRoleRepository` | `find_by_name` only |
| `mappers.py` | `user_orm_to_domain` / `apply_domain_to_user_orm` |
| `RedisRefreshTokenStore` | `refresh_token:{token}` → `user_id` |
| `RedisRevocationStore` | `revoked_jti:{jti}` with TTL |
| `BcryptPasswordHasher` | Wraps `passlib.CryptContext` with bcrypt + legacy PBKDF2 |
| `JwtTokenIssuer` | RS256 JWT with full claims |
| `JwtTokenVerifier` | Validates signature, expiry, issuer; raises `InvalidTokenError` / `TokenExpiredError` |
| `composition.py` | Wires all adapters into use case instances |
| `http/routes.py` | FastAPI route handlers (thin: validate → execute → serialize) |
| `http/schemas.py` | Pydantic request/response models |
| `http/dependencies.py` | `get_current_user`, `require_super_user` |
| `http/exception_mapper.py` | Maps domain exceptions to HTTP status codes |
| `http/jwks.py` | `GET /.well-known/jwks.json` — serves RSA public key in JWK format |
| `crypto/key_pair.py` | `RSAKeyPair` singleton; loads PEM keys at startup |

---

## RBAC Context (`app/rbac/`)

Manages roles, permissions, and user-role assignments. All mutations emit domain events that the Unit of Work dispatches to the audit logger after commit.

### Domain ports (`app/rbac/domain/ports/`)

| Port | Methods |
|------|---------|
| `RoleRepository` | `find_by_id`, `find_by_name`, `add`, `mark_deleted` |
| `PermissionRepository` | `find_by_scope_key(ScopeKey)`, `add(ScopeKey)` |
| `AssignmentRepository` | `role_has_permission`, `assign_permission`, `revoke_permission`, `assign_role_to_user`, `revoke_role_from_user` |
| `UserReader` | `find_summary_by_id` (read-only, returns `UserSummary`) |
| `RbacUnitOfWork` | async context manager, `commit`, `rollback`, `add_event`, all repos above |

### Domain events (`app/rbac/domain/events.py`)

All events are immutable frozen dataclasses extending `DomainEvent`. Each has a `to_audit_payload()` method.

`RoleCreated` · `RoleDeleted` · `PermissionGranted` · `PermissionRevoked` · `UserRoleAssigned` · `UserRoleRevoked`

### Use cases (`app/rbac/application/use_cases/`)

| Use Case | Event emitted |
|----------|--------------|
| `CreateRoleUseCase` | `RoleCreated` |
| `DeleteRoleUseCase` | `RoleDeleted` — calls `role.assert_deletable()` first |
| `AssignPermissionUseCase` | `PermissionGranted` — auto-creates Permission if not found |
| `RevokePermissionUseCase` | `PermissionRevoked` |
| `AssignRoleToUserUseCase` | `UserRoleAssigned` |
| `RevokeRoleFromUserUseCase` | `UserRoleRevoked` |

Pattern in every use case:
```python
async with self._uow_factory() as uow:
    # ... business logic ...
    uow.add_event(SomeEvent(...))
    await uow.commit()   # commits DB, then dispatches events → audit logs
```

### Infrastructure adapters (`app/rbac/infrastructure/`)

| Adapter | Description |
|---------|-------------|
| `SqlAlchemyRbacUnitOfWork` | Commits RBAC changes, then dispatches events via `AuditLoggingHandler` and commits audit logs |
| `SqlAlchemyRoleRepository` | Role CRUD with soft delete |
| `SqlAlchemyPermissionRepository` | Looks up / creates permissions by `ScopeKey` |
| `SqlAlchemyAssignmentRepository` | Manages `role_permissions` and `user_roles` join tables |
| `SqlAlchemyUserReader` | Read-only user summary lookup |
| `composition.py` | Wires `SqlAlchemyAuditLogger` into the UoW factory |
| `http/routes.py` | FastAPI admin route handlers |
| `http/schemas.py` | Pydantic request/response models |

---

## Audit Context (`app/audit/`)

Read-only — serves paginated audit log entries. Writes come via domain event dispatch from the RBAC UoW.

### Domain ports (`app/audit/domain/ports/`)

| Port | Methods |
|------|---------|
| `AuditLogReader` | `list_paginated(page, page_size) -> list[AuditLog]` |

### Use cases (`app/audit/application/use_cases/`)

`GetAuditLogsUseCase` — calls `AuditLogReader.list_paginated`.

### Infrastructure adapters (`app/audit/infrastructure/`)

| Adapter | Description |
|---------|-------------|
| `SqlAlchemyAuditLogger` | Implements the shared `AuditLogger` port; calls `session.add(AuditLogORM)` (no commit — caller commits) |
| `SqlAlchemyAuditLogReader` | Reads audit logs ordered by `created_at DESC` |
| `http/routes.py` | `GET /admin/audit-logs` paginated endpoint |

---

## Shared Layer (`app/shared/`)

### Domain (`app/shared/domain/`)

| Module | Contents |
|--------|----------|
| `entities/user.py` | `User` dataclass with `is_authenticatable()` |
| `entities/role.py` | `Role` dataclass with `assert_deletable()` |
| `entities/permission.py` | `Permission` dataclass (scope_key is a `ScopeKey` value object) |
| `entities/audit_log.py` | `AuditLog` dataclass (read-only) |
| `values/email.py` | `Email` — frozen dataclass, validates `@` + domain |
| `values/scope_key.py` | `ScopeKey` — frozen dataclass, `resource:action`; `ScopeKey.parse(str)` |
| `events.py` | `DomainEvent` base, `EventDispatcher` / `EventHandler` protocols |
| `exceptions.py` | `DomainError`, `SystemRoleProtectedError` |
| `ports/audit_logger.py` | `AuditLogger` protocol (shared across RBAC → Audit) |

### Infrastructure (`app/shared/infrastructure/`)

| Module | Contents |
|--------|----------|
| `crypto/bcrypt_password_hasher.py` | `BcryptPasswordHasher` — wraps `passlib` |
| `crypto/jwt_token_issuer.py` | `JwtTokenIssuer` — wraps PyJWT encode |
| `crypto/jwt_token_verifier.py` | `JwtTokenVerifier` — wraps PyJWT decode |
| `db/base.py` | `Base`, `TimestampMixin`, `SoftDeleteMixin` |
| `db/session.py` | `async_engine`, `async_session_factory`, `get_db` (for legacy admin routes) |
| `cache/redis.py` | `redis_client` singleton |
| `cache/pubsub.py` | GCP Pub/Sub client |
| `events/audit_handler.py` | `AuditLoggingHandler` — maps RBAC domain events to `AuditLogger.log()` calls |
| `events/simple_dispatcher.py` | `SimpleEventDispatcher` — in-memory dispatcher |
| `http/rate_limit.py` | `rate_limit_by_ip`, `rate_limit_by_username` FastAPI dependencies |

---

## Core (`app/core/`)

Cross-cutting concerns that are not part of any bounded context.

| Module | Contents |
|--------|----------|
| `logging.py` | `JSONFormatter`, `setup_logging` — structured JSON logs for GCP Cloud Logging |
| `middleware.py` | `RequestResponseMiddleware` — injects `X-Request-ID` |
| `context.py` | `ContextVar` for request ID propagation |

---

## App Entry Point (`app/main.py`)

- Creates `FastAPI` app with lifespan context manager
- Lifespan: loads RSA keys, pings DB + Redis on startup; closes connections on shutdown
- Registers routers: auth routes, RBAC routes, audit routes, JWKS
- Registers exception handlers via `register_auth_exception_handlers`, `register_rbac_exception_handlers`
