# Authentication & Authorisation Flows

## Token Architecture

```mermaid
graph LR
    subgraph Tokens
        AT[Access Token<br/>RS256 JWT<br/>15 min TTL<br/>Authorization header]
        RT[Refresh Token<br/>urlsafe 64-byte secret<br/>7 day TTL<br/>httpOnly cookie]
    end

    subgraph Storage
        JTI[(Redis<br/>JTI revocation set)]
        RTS[(Redis<br/>refresh_token → user_id)]
    end

    AT -->|jti checked on every request| JTI
    RT -->|stored on login, rotated on refresh, deleted on logout| RTS
```

**Access token claims:** `sub`, `iss`, `iat`, `exp`, `jti`, `username`, `roles[]`, `permissions[]`, `is_super_user`

---

## Signup

```mermaid
sequenceDiagram
    participant C as Client
    participant R as auth/routes.py
    participant UC as SignupUseCase
    participant UoW as AuthUnitOfWork
    participant DB as PostgreSQL

    C->>R: POST /api/v1/auth/signup
    R->>R: rate_limit_by_ip (20/min)
    R->>UC: execute(SignupInput)
    UC->>UoW: find_by_username / find_by_email
    UoW->>DB: SELECT users

    alt username or email taken
        UC-->>R: UserExistsError
        R-->>C: 409 Conflict
    else
        UC->>UC: hasher.hash(password)
        UC->>UoW: users.add(User)
        UC->>UoW: roles.find_by_name("viewer")
        alt viewer role missing
            UC-->>R: DefaultRoleMissingError
            R-->>C: 500
        else
            UC->>UoW: commit()
            UoW->>DB: INSERT users + user_roles
            R-->>C: 201 {id, username, email, created_at}
        end
    end
```

---

## Login

```mermaid
sequenceDiagram
    participant C as Client
    participant R as auth/routes.py
    participant UC as LoginUseCase
    participant DB as PostgreSQL
    participant Redis

    C->>R: POST /api/v1/auth/login
    R->>R: rate_limit_by_ip (20/min)<br/>rate_limit_by_username (5/5 min)
    R->>UC: execute(LoginInput)
    UC->>DB: SELECT user + selectinload roles→permissions

    alt user not found or is_active=false
        UC-->>R: InvalidCredentialsError
        R-->>C: 401
    else
        UC->>UC: hasher.verify(password, hash)
        alt wrong password
            UC-->>R: InvalidCredentialsError
            R-->>C: 401
        else
            opt hash.needs_rehash()
                UC->>DB: UPDATE users SET password_hash=bcrypt(password)
            end
            UC->>UC: token_issuer.issue(TokenClaims)
            UC->>UC: secrets.token_urlsafe(64)
            UC->>Redis: SETEX refresh_token:<token> user_id 604800
            R-->>C: 200 {access_token, token_type}<br/>Set-Cookie: refresh_token=... HttpOnly SameSite=Lax
        end
    end
```

---

## Token Refresh

```mermaid
sequenceDiagram
    participant C as Client
    participant R as auth/routes.py
    participant UC as RefreshTokenUseCase
    participant Redis
    participant DB as PostgreSQL

    C->>R: POST /api/v1/auth/refresh (Cookie: refresh_token)
    R->>R: rate_limit_by_ip
    R->>UC: execute(RefreshInput)
    UC->>Redis: GET refresh_token:<token>

    alt not found or expired
        UC-->>R: RefreshTokenInvalidError
        R-->>C: 401
    else
        UC->>DB: SELECT user + roles + permissions
        UC->>UC: token_issuer.issue(new TokenClaims)
        UC->>UC: secrets.token_urlsafe(64)
        UC->>Redis: DEL refresh_token:<old>
        UC->>Redis: SETEX refresh_token:<new> user_id 604800
        R-->>C: 200 {access_token}<br/>Set-Cookie: refresh_token=<new> HttpOnly
    end
```

---

## Logout

```mermaid
sequenceDiagram
    participant C as Client
    participant R as auth/routes.py
    participant Dep as get_current_user
    participant UC as LogoutUseCase
    participant Redis

    C->>R: POST /api/v1/auth/logout (Bearer + Cookie)
    R->>Dep: validate token
    Dep->>Redis: GET revoked_jti:<jti>
    alt already revoked
        Dep-->>C: 401
    else
        R->>UC: execute(LogoutInput)
        UC->>Redis: DEL refresh_token:<token>
        UC->>Redis: SETEX revoked_jti:<jti> "1" <remaining_ttl>
        R-->>C: 204 No Content<br/>Set-Cookie: refresh_token= Max-Age=0
    end
```

---

## Protected Endpoint — Token Validation

Every request to a protected route goes through `get_current_user` before the handler runs.

```mermaid
sequenceDiagram
    participant C as Client
    participant R as Protected Route
    participant Dep as get_current_user
    participant Verif as JwtTokenVerifier
    participant Redis

    C->>R: GET /api/v1/auth/me (Authorization: Bearer <token>)
    R->>Dep: HTTPBearer extracts token
    Dep->>Verif: verify(token)
    Verif->>Verif: decode RS256 with public key<br/>check exp, iss, sub, jti

    alt invalid signature / expired
        Verif-->>Dep: InvalidTokenError / TokenExpiredError
        Dep-->>C: 401
    else
        Dep->>Redis: GET revoked_jti:<jti>
        alt revoked
            Dep-->>C: 401 Token revoked
        else
            Dep-->>R: TokenPayload dict
            R-->>C: 200 response
        end
    end
```

---

## Admin Endpoint — Super User Guard

RBAC mutation routes add `require_super_user` on top of `get_current_user`.

```mermaid
flowchart TD
    REQ[Incoming request] --> GCU[get_current_user<br/>validate JWT + revocation]
    GCU -->|401| ERR1[Unauthorized]
    GCU -->|TokenPayload| RSU[require_super_user<br/>check is_super_user claim]
    RSU -->|false| ERR2[403 Forbidden]
    RSU -->|true| HANDLER[Route handler<br/>→ use case]
```

---

## RBAC Mutation with Domain Event → Audit

Every admin write operation follows this pattern. The audit log is written in the same DB transaction via the Unit of Work — no eventual consistency risk.

```mermaid
sequenceDiagram
    participant Admin
    participant Route as rbac/routes.py
    participant UC as RBAC Use Case
    participant UoW as SqlAlchemyRbacUnitOfWork
    participant DB as PostgreSQL

    Admin->>Route: POST /api/v1/admin/roles (super user token)
    Route->>UC: execute(input)
    UC->>UoW: mutation (roles.add / assignments.assign_permission / ...)

    alt domain invariant violated
        UC-->>Route: domain exception
        Route-->>Admin: 409 / 404
    else
        UC->>UoW: add_event(RoleCreated / PermissionGranted / ...)
        UC->>UoW: commit()
        UoW->>DB: INSERT / UPDATE — COMMIT
        UoW->>UoW: collect_events()
        UoW->>UoW: SqlAlchemyAuditLogger.log(event)
        UoW->>DB: INSERT audit_logs — COMMIT
        Route-->>Admin: 201 / 204
    end
```

---

## Rate Limiting Logic

```mermaid
flowchart LR
    REQ[Request] --> IP{rate_limit_by_ip<br/>INCR key<br/>EXPIRE 60s}
    IP -->|count ≤ 20| NEXT[Continue]
    IP -->|count > 20| R429_IP[429 Too Many Requests<br/>Retry-After: TTL]

    NEXT --> UN{rate_limit_by_username<br/>login only<br/>INCR key<br/>EXPIRE 300s}
    UN -->|count ≤ 5| HANDLER[Handler]
    UN -->|count > 5| R429_UN[429 Too Many Requests]
```
