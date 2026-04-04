# Sequence Diagrams

This document provides visual sequence diagrams for key flows in the Access Control Service, using Mermaid syntax.

---

## 1. User Signup Flow

```mermaid
sequenceDiagram
    participant Client
    participant API as API Layer (auth.py)
    participant RateLimit as Rate Limiter
    participant Service as AuthService
    participant DB as PostgreSQL
    participant Redis as Redis

    Client->>API: POST /auth/signup<br/><{username,password,email}>
    API->>RateLimit: Check IP rate limit
    RateLimit-->>API: OK / Too Many Requests
    alt Rate limited
        RateLimit-->>Client: 429 Too Many Requests
    else
        API->>Service: signup(db, data)
        Service->>DB: SELECT * FROM users<br/>WHERE username = data.username
        DB-->>Service: User or None
        alt User exists
            Service-->>API: raise UniquenessError
            API-->>Client: 400 Bad Request
        else
            Service->>DB: SELECT * FROM roles<br/>WHERE name = 'viewer'
            DB-->>Service: Role
            Service->>DB: INSERT INTO users (...)
            Service->>DB: FLUSH (get user.id)
            Service->>DB: INSERT INTO user_roles (user_id,role_id)
            Service->>DB: COMMIT
            Service-->>API: User object
            API-->>Client: 201 Created<br/>{id,username,email,created_at}
        end
    end
```

**Key Points**:
- Rate limiting by IP applied upfront
- Uniqueness check for username (and email if provided)
- Viewer role must exist in database (seeded separately)
- Transaction commits in API layer after service returns

---

## 2. User Login Flow

```mermaid
sequenceDiagram
    participant Client
    participant API as API Layer (auth.py)
    participant RateIP as IP Rate Limit
    participant RateUser as Username Rate Limit
    participant Service as AuthService
    participant DB as PostgreSQL
    participant Redis as Redis
    participant JWT as JWT Library

    Client->>API: POST /auth/login<br/><{username,password}>
    API->>RateIP: Check IP limit
    RateIP-->>API: OK / 429
    alt IP rate limited
        RateIP-->>Client: 429 Too Many Requests
    else
        API->>RateUser: Check username limit
        RateUser-->>API: OK / 429
        alt Username rate limited
            RateUser-->>Client: 429 Too Many Requests
        else
            API->>Service: login(db, data)
            Service->>DB: SELECT user with roles/permissions<br/>WHERE username = data.username
            DB-->>Service: User (with .roles, .permissions) or None
            alt User not found or bad password
                Service-->>API: raise InvalidCredentialsError
                API-->>Client: 401 Unauthorized
            else
                Service->>Service: needs_rehash(password_hash)?<br/>(lazy migration)
                alt Needs rehash (old bcrounds or PBKDF2)
                    Service->>Service: hash_password(new)
                    Service->>DB: UPDATE user.password_hash
                end
                Service->>JWT: create_access_token(...)
                JWT-->>Service: access_token (RS256 signed)
                Service->>Service: generate refresh_token (64 bytes)
                Service->>Redis: SETEX refresh_token:{token} 7days user_id
                Redis-->>Service: OK
                Service-->>API: (access_token, refresh_token)
                API-->>Client: 200 OK {access_token}
                API->>Client: 'Set-Cookie: refresh_token=...#59; HttpOnly'
            end
        end
    end
```

**Key Points**:
- Double rate limiting: IP (20/min) and username (5/5min)
- Eager loading with `selectinload` to avoid N+1 queries
- Lazy bcrypt migration triggered if `needs_rehash()`
- Refresh token stored in Redis with 7-day TTL
- Refresh token sent as httpOnly cookie (not in JSON body)

---

## 3. Token Refresh Flow

```mermaid
sequenceDiagram
    participant Client
    participant API as API Layer (auth.py)
    participant RateIP as Rate Limiter
    participant Service as AuthService
    participant DB as PostgreSQL
    participant Redis as Redis
    participant JWT as JWT Library

    Client->>API: POST /auth/refresh<br/>(cookie: refresh_token)
    API->>RateIP: Check IP limit
    RateIP-->>API: OK / 429
    alt Rate limited
        RateIP-->>Client: 429 Too Many Requests
    else
        API->>API: Extract refresh_token from cookies
        alt No cookie
            API-->>Client: 401 Unauthorized
        else
            API->>Service: refresh_token(db, refresh_token)
            Service->>Redis: GET refresh_token:{token}
            Redis-->>Service: user_id (or None)
            alt Token not in Redis
                Service-->>API: raise InvalidTokenError
                API-->>Client: 401 Unauthorized
            else
                Service->>DB: SELECT user with roles/permissions<br/>WHERE id = user_id
                DB-->>Service: User
                alt User not found or deleted/inactive
                    Service-->>API: raise InvalidTokenError
                else
                    Service->>JWT: create_access_token(...)
                    JWT-->>Service: new_access_token
                    Service->>Service: generate new_refresh_token
                    Service->>Redis: DELETE refresh_token:{old_token}
                    Service->>Redis: SETEX refresh_token:{new_token} 7days user_id
                    Service-->>API: (new_access_token, new_refresh_token)
                    API-->>Client: 200 OK {access_token}
                    API->>Client: 'Set-Cookie: refresh_token=new...'
                end
            end
        end
    end
```

**Key Points**:
- Refresh token rotation: old token deleted, new token issued
- Prevents replay attacks: stolen refresh token can only be used once
- Both tokens returned in responses; client must update cookie
- User re-fetched from DB; if user deleted, refresh fails
- Rate limiting by IP to prevent abuse

---

## 4. Token Revocation (Logout)

```mermaid
sequenceDiagram
    participant Client
    participant API as API Layer (auth.py)
    participant Service as AuthService
    participant Redis as Redis

    Client->>API: POST /auth/logout<br/> headers: Bearer <access_token><br/>cookie: refresh_token
    API->>API: get_current_user dependency<br/>(validates access token, checks JTI)
    API-->>Client: 401 if invalid/revoked

    API->>Service: logout(refresh_token, payload)
    Service->>Redis: DELETE refresh_token:{token}
    Service->>Redis: GET payload["exp"], calculate ttl_remaining
    Service->>Redis: SETEX revoked_jti:{jti} ttl_remaining "1"
    Redis-->>Service: OK
    Service-->>API: None
    API-->>Client: 204 No Content
    API->>Client: 'Set-Cookie: refresh_token=#59; Max-Age=0'
```

**Key Points**:
- Access token remains valid until expiry, but JTI revoked in Redis
- Refresh token immediately deleted from Redis
- Subsequent requests with access token will fail due to JTI check
- New refresh token cannot be issued (existing one deleted)
- Logout does not immediately invalidate access token; relies on client to stop using it

---

## 5. Protected Endpoint Access

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant Dep as get_current_user
    participant Security as security.verify_access_token
    participant Redis as Redis
    participant Route as Protected Route

    Client->>API: GET /auth/me<br/>Authorization: Bearer <token>
    API->>Dep: get_current_user(bearer)
    Dep->>Security: verify_access_token(token)
    Security->>Security: Decode JWT, verify signature<br/>(uses RSA public key)
    Security-->>Dep: payload dict
    Dep->>Redis: GET revoked_jti:{jti}
    Redis-->>Dep: "1" (revoked) or None
    alt JTI revoked
        Dep-->>API: raise HTTPException(401)
        API-->>Client: 401 Unauthorized
    else
        Dep-->>API: TokenPayload
        API->>Route: handler(payload)
        Route-->>API: MeResponse
        API-->>Client: 200 OK {data}
    end
```

**Key Points**:
- Dependency chain: `get_current_user` runs before route handler
- Token signature verified against RSA public key
- JTI revocation checked on EVERY request
- Returns 401 if token expired, invalid signature, or revoked
- Payload injected as `TokenPayload` for route use

---

## 6. Create Role (Admin)

```mermaid
sequenceDiagram
    participant SuperUser as Super User Client
    participant API as API Layer (/admin/roles)
    participant Service as RBACService
    participant DB as PostgreSQL
    participant Redis as (not used)

    SuperUser->>API: POST /admin/roles<br/>{name,description}<br/>Bearer: <super_token>
    API->>API: require_super_user dependency<br/>(checks is_super_user in token)
    alt Not super user
        API-->>SuperUser: 403 Forbidden
    else
        API->>Service: create_role(db, data, actor_id)
        Service->>DB: SELECT * FROM roles WHERE name = data.name
        DB-->>Service: None (name available)
        Service->>DB: INSERT INTO roles (name,description,created_by)
        Service->>DB: FLUSH (get role.id)
        Service->>DB: INSERT INTO audit_logs<br/>(action=ROLE_CREATED, payload)
        Service->>DB: COMMIT
        Service-->>API: Role object
        API-->>SuperUser: 201 Created RoleResponse
    end
```

**Key Points**:
- `require_super_user` dependency checked before invoking service
- Role name uniqueness enforced
- Audit log entry created in same transaction
- Service does not commit; caller (API layer) commits after response prepared (but in practice service flush/refresh requires commit before return; see note in component details)

---

## 7. Assign Permission to Role (Auto-Creation)

```mermaid
sequenceDiagram
    participant Admin
    participant API as /admin/roles/{id}/permissions
    participant Service as RBACService
    participant DB as PostgreSQL

    Admin->>API: POST /admin/roles/123/permissions<br/>{resource:"users", action:"read"}
    API->>API: require_super_user (OK)
    API->>Service: assign_permission(db, role_id, data, actor_id)

    Service->>DB: SELECT role WHERE id=123 (with permissions)
    DB-->>Service: Role object
    alt Role not found or deleted
        Service-->>API: raise NotFoundError → 404
    else
        Service->>Service: scope_key = f"{resource}:{action}"
        Service->>DB: SELECT permission WHERE scope_key = scope_key
        DB-->>Service: None
        Service->>DB: INSERT INTO permissions (resource,action,scope_key)
        Service->>DB: FLUSH (get permission.id)
        Service->>DB: SELECT * FROM role_permissions<br/>WHERE role_id=123 AND permission_id=...
        DB-->>Service: None (not already assigned)
        Service->>DB: INSERT INTO role_permissions (...) 
        Service->>DB: INSERT INTO audit_logs (PERMISSION_GRANTED)
        Service->>DB: COMMIT
        Service-->>API: RolePermission object
        API-->>Admin: 201 Created RolePermissionResponse
    end
```

**Key Points**:
- Permission auto-created if scope_key missing
- Double-check to avoid duplicate association (DB query bypassing session cache)
- Audit log records actor and both IDs

---

## 8. Get Audit Logs (Paginated)

```mermaid
sequenceDiagram
    participant Admin
    participant API as /admin/audit-logs
    participant Service as RBACService
    participant DB as PostgreSQL

    Admin->>API: GET /admin/audit-logs?page=2&page_size=50
    API->>API: require_super_user (OK)
    API->>Service: get_audit_logs(db, page=2, page_size=50)
    Service->>Service: offset = (2 - 1) * 50 = 50
    Service->>DB: SELECT * FROM audit_logs<br/>ORDER BY created_at DESC<br/>OFFSET 50 LIMIT 50
    DB-->>Service: list[AuditLog]
    Service-->>API: list[AuditLog]
    API-->>Admin: 200 OK [ {log1}, {log2}, ... ]
```

**Key Points**:
- Pagination via `OFFSET` and `LIMIT`
- Ordered by most recent first (`created_at DESC`)
- No filter by actor or action (could be added if needed)
- Returns raw JSONB payload from DB as dict

---

## 9. JWKS Endpoint

```mermaid
sequenceDiagram
    participant Client
    participant API as jwks.py
    participant Keys as RSAKeyPair

    Client->>API: GET /.well-known/jwks.json
    API->>Keys: get_key_pair() → (private, public)
    Keys-->>API: public_key (cryptography object)
    API->>API: Extract modulus (n) and exponent (e)
    API->>API: base64url_encode(n), base64url_encode(e)
    API->>API: kid = SHA256(public_key_der)[:16].base64url()
    API-->>Client: 200 OK {"keys":[{kty:"RSA",use:"sig",kid:"...",n:"...",e:"AQAB"}]}
```

**Key Points**:
- Public key only; private never exposed
- `kid` derived from public key content (consistent across restarts if same key)
- Base64url encoding without padding as per JWK spec
- Single key currently; multi-key rotation would require storing multiple keys and selecting by `kid` in JWT header

---

## 10. Rate Limit Enforcement (IP)

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Redis

    Client->>API: POST /auth/login (1st request)
    API->>Redis: INCR rate_limit:ip:{ip}:/auth/login
    Redis-->>API: 1 (new key)
    API->>Redis: EXPIRE key 60
    Redis-->>API: OK
    API-->>API: Continue to handler
    API->>API: Handle login logic...
    API-->>Client: 200 OK

    Note over Client,Redis: Subsequent requests...

    Client->>API: POST /auth/login (21st request within 60s)
    API->>Redis: INCR key
    Redis-->>API: 21 (exceeds 20)
    API-->>Redis: TTL key (to get retry_after)
    Redis-->>API: 45 seconds remaining
    API-->>Client: 429 Too Many Requests<br/>Retry-After: 45
```

**Key Points**:
- Key includes IP address AND endpoint path
- TTL set on first request; subsequent requests don't reset it
- Counter increments atomically via Redis INCR
- 429 includes `Retry-After` header with seconds to wait

---

## 11. Super User Dependency Check

```mermaid
sequenceDiagram
    participant AdminClient
    participant API
    participant Dep1 as get_current_user
    participant Dep2 as require_super_user
    participant Security
    participant Redis

    AdminClient->>API: POST /admin/roles<br/>Bearer: <token>
    API->>Dep1: get_current_user()
    Dep1->>Security: verify_access_token(token)
    Security-->>Dep1: payload
    Dep1->>Redis: GET revoked_jti:{jti}
    Redis-->>Dep1: None
    Dep1-->>API: TokenPayload (is_super_user=False?)
    API->>Dep2: require_super_user(payload)
    alt is_super_user == True
        Dep2-->>API: payload (OK)
        API->>Route: handler()
        Route-->>API: Response
        API-->>AdminClient: 200/201
    else
        Dep2-->>API: raise 403
        API-->>AdminClient: 403 Forbidden<br/>"Super user privilege required"
    end
```

**Key Points**:
- Dependencies are chained: `require_super_user` depends on `get_current_user`
- Both executed before route handler
- 403 raised before any business logic runs

---

## References

- Auth endpoints: `app/api/v1/auth.py:14-192`
- Admin endpoints: `app/api/v1/admin.py:16-291`
- JWKS: `app/api/v1/jwks.py:13-59`
- AuthService: `app/services/auth_service.py:39-269`
- RBACService: `app/services/rbac_service.py:22-293`
- Security: `app/core/security.py:13-81`
- Dependencies: `app/core/dependencies.py:14-66`
- Rate limiting: `app/core/rate_limit.py:15-70`
