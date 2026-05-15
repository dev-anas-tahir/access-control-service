# IAM Service — Domain Context

## Bounded Contexts

| Context | Aggregates / Entities | Responsibility |
|---------|----------------------|----------------|
| `auth/` | `User`, `AccessToken`, `RefreshToken` | Identity, credential verification, token lifecycle |
| `rbac/` | `Role`, `Permission`, user-role assignments | Role and permission management, RBAC mutations |
| `audit/` | `AuditLog` | Immutable record of every RBAC mutation |

---

## Glossary

### User
The primary identity entity. Has a `username`, `password_hash`, and lifecycle flags (`is_active`, `is_deleted`). Belongs to at most one `organization_id`. Carries a snapshot of assigned `Role` objects (each with their `Permission` list) that is loaded eagerly via `selectinload`. A `User` is never directly authorized — authorization is derived from the permissions embedded in their issued tokens.

### Superuser
A `User` with `is_super_user = True`. The only principal allowed to perform RBAC mutations (create/delete roles, grant/revoke permissions, assign/revoke user-role associations). Checked via the `require_super_user` FastAPI dependency, which reads the `is_super_user` claim from the JWT — not from the database.

### Role
A named, reusable collection of `Permission` objects. Has an `is_system` flag for built-in roles that must not be deleted. User-created roles are always `is_system = False`. Deletion is a soft-delete (`is_deleted = True`); the row is never removed.

### Permission
A single, granular capability expressed as a `ScopeKey`. Permissions are shared across roles — the same `Permission` row can be granted to multiple roles. Permissions are never soft-deleted; they are only revoked (removed from the association table).

### ScopeKey
A value object in the format `resource:action` (e.g. `catalog:write`, `orders:read`). Resource and action are lowercase strings. The colon is the only separator — colons are forbidden inside the resource or action segments. `ScopeKey` enforces this format at construction time.

### AccessToken
A short-lived RS256-signed JWT (default 15 min). Carries a full snapshot of the user's roles and permissions at issuance time. Claims: `sub` (user UUID), `username`, `roles` (list of names), `permissions` (list of scope keys), `is_super_user`, `jti`, `iss`, `exp`. Because it embeds a permissions snapshot, permission changes take effect only after the current access token expires.

### RefreshToken
An opaque random token with 7-day expiry. Stored in Redis keyed by the token value (`refresh_token:<token> → user_id`). Delivered exclusively via `Set-Cookie: refresh_token; HttpOnly; SameSite=Lax`. Never included in response bodies. Single-use: consuming a refresh token immediately revokes it and issues a new pair.

### JTI (JWT ID)
A UUID embedded in every `AccessToken`. On logout, the JTI is written to the Redis revocation set (`revoked_jti:<jti>`) with TTL equal to the token's remaining lifetime. Every protected request must check this set — a valid signature is not sufficient for authorization if the JTI is revoked.

### AuditLog
An immutable append-only record written after every successful RBAC mutation. Fields: `actor_id`, `action` (e.g. `role_created`), `entity_type`, `entity_id`, `payload: dict`, `created_at`. Never updated or deleted. Written indirectly via domain events — RBAC use cases emit events; the Unit of Work dispatches them to `SqlAlchemyAuditLogger` after commit.

### Domain Events (RBAC)
Emitted by RBAC use cases to decouple mutation logic from audit logging. Each event implements `to_audit_payload() -> dict`.

| Event | Trigger |
|-------|---------|
| `RoleCreated` | A new role is persisted |
| `RoleDeleted` | A role is soft-deleted |
| `PermissionGranted` | A permission is added to a role |
| `PermissionRevoked` | A permission is removed from a role |
| `UserRoleAssigned` | A role is assigned to a user |
| `UserRoleRevoked` | A role is revoked from a user |

---

## Authorization Model

This service **is** the authorization authority. It does not validate tokens against another service. Downstream services (e.g. catalog-service) verify tokens by fetching the RS256 public key from `GET /.well-known/jwks.json`.

- All `POST /api/v1/auth/*` routes are public (rate-limited).
- All `POST/DELETE /api/v1/admin/*` routes require `is_super_user = true` in the JWT claim.
- `GET /api/v1/audit/*` routes require a valid JWT (any authenticated user).

---

## Key Invariants

- `is_system` roles cannot be soft-deleted.
- A `Permission` with a given `ScopeKey` is unique — attempting to create a duplicate is a conflict.
- `RefreshToken` is single-use. Reuse after rotation is rejected via JTI revocation.
- The `AccessToken` permissions snapshot may lag real RBAC state by up to `ACCESS_TOKEN_EXPIRE_MINUTES`. This is a known trade-off of stateless tokens.
- `password_hash` is never exposed in any API response schema.
- Audit log entries are never mutated or deleted — no update or delete path exists in the `AuditLogger` port.
