# Sequence Diagrams

Key flows in the Access Control Service.

---

## 1. User Signup

```mermaid
sequenceDiagram
    participant Client
    participant Route as auth/routes.py
    participant UC as SignupUseCase
    participant UoW as AuthUnitOfWork
    participant DB as PostgreSQL

    Client->>Route: POST /api/v1/auth/signup
    Route->>Route: rate_limit_by_ip
    Route->>UC: execute(SignupInput)
    UC->>UoW: find_by_username / find_by_email
    UoW->>DB: SELECT users
    alt username or email exists
        UC-->>Route: raise UserExistsError
        Route-->>Client: 409 Conflict
    else
        UC->>UC: hasher.hash(password)
        UC->>UoW: users.add(User)
        UC->>UoW: roles.find_by_name("viewer")
        alt viewer role missing
            UC-->>Route: raise DefaultRoleMissingError
            Route-->>Client: 500
        else
            UC->>UoW: commit()
            UoW->>DB: INSERT users + user_roles
            Route-->>Client: 201 Created
        end
    end
```

---

## 2. User Login

```mermaid
sequenceDiagram
    participant Client
    participant Route as auth/routes.py
    participant UC as LoginUseCase
    participant UoW as AuthUnitOfWork
    participant DB as PostgreSQL
    participant Redis

    Client->>Route: POST /api/v1/auth/login
    Route->>Route: rate_limit_by_ip + rate_limit_by_username
    Route->>UC: execute(LoginInput)
    UC->>UoW: users.find_by_username (eager-loads roles+permissions)
    UoW->>DB: SELECT user + selectinload roles/permissions
    alt user not found or inactive
        UC-->>Route: raise InvalidCredentialsError
        Route-->>Client: 401
    else
        UC->>UC: hasher.verify(password, hash)
        alt wrong password
            UC-->>Route: raise InvalidCredentialsError
            Route-->>Client: 401
        else
            opt needs_rehash
                UC->>UoW: users.update(user with new hash)
            end
            UC->>UC: token_issuer.issue(claims)
            UC->>UC: secrets.token_urlsafe(64)
            UC->>Redis: refresh_store.put(token, user_id, ttl)
            UC->>UoW: commit()
            Route-->>Client: 200 {access_token} + Set-Cookie: refresh_token
        end
    end
```

---

## 3. Token Refresh

```mermaid
sequenceDiagram
    participant Client
    participant Route as auth/routes.py
    participant UC as RefreshTokenUseCase
    participant Redis
    participant UoW as AuthUnitOfWork
    participant DB as PostgreSQL

    Client->>Route: POST /api/v1/auth/refresh (cookie: refresh_token)
    Route->>UC: execute(RefreshInput)
    UC->>Redis: refresh_store.get(token)
    alt not found
        UC-->>Route: raise RefreshTokenInvalidError
        Route-->>Client: 401
    else
        UC->>UoW: users.find_by_id (eager-loads roles+permissions)
        UoW->>DB: SELECT user
        UC->>UC: token_issuer.issue(new claims)
        UC->>UC: generate new refresh token
        UC->>Redis: refresh_store.delete(old)
        UC->>Redis: refresh_store.put(new, user_id, ttl)
        UC->>UoW: commit()
        Route-->>Client: 200 {access_token} + Set-Cookie: new refresh_token
    end
```

---

## 4. Logout

```mermaid
sequenceDiagram
    participant Client
    participant Route as auth/routes.py
    participant Dep as get_current_user
    participant UC as LogoutUseCase
    participant Redis

    Client->>Route: POST /api/v1/auth/logout (Bearer + cookie)
    Route->>Dep: validate token + check JTI revocation
    Dep->>Redis: revocation_store.is_revoked(jti)
    alt revoked
        Dep-->>Client: 401
    else
        Route->>UC: execute(LogoutInput)
        UC->>Redis: refresh_store.delete(token)
        UC->>Redis: revocation_store.revoke(jti, remaining_ttl)
        Route-->>Client: 204 No Content + clear cookie
    end
```

---

## 5. Protected Endpoint (Token Validation)

```mermaid
sequenceDiagram
    participant Client
    participant Route as any protected route
    participant Dep as get_current_user
    participant Verifier as JwtTokenVerifier
    participant Redis

    Client->>Route: GET /api/v1/auth/me (Bearer token)
    Route->>Dep: get_current_user(bearer)
    Dep->>Verifier: verify(token)
    Verifier->>Verifier: decode RS256 signature
    alt invalid / expired
        Verifier-->>Dep: raise InvalidTokenError / TokenExpiredError
        Dep-->>Client: 401
    else
        Dep->>Redis: revocation_store.is_revoked(jti)
        alt revoked
            Dep-->>Client: 401 Token revoked
        else
            Dep-->>Route: TokenPayload
            Route-->>Client: 200 {me data}
        end
    end
```

---

## 6. Create Role (RBAC with Domain Events)

```mermaid
sequenceDiagram
    participant Admin
    participant Route as rbac/routes.py
    participant UC as CreateRoleUseCase
    participant UoW as SqlAlchemyRbacUnitOfWork
    participant DB as PostgreSQL

    Admin->>Route: POST /api/v1/admin/roles (super user token)
    Route->>Route: require_super_user
    Route->>UC: execute(CreateRoleInput)
    UC->>UoW: roles.find_by_name (check uniqueness)
    alt name taken
        UC-->>Route: raise RoleAlreadyExistsError
        Route-->>Admin: 409
    else
        UC->>UoW: roles.add(name, description, created_by)
        UC->>UoW: add_event(RoleCreated(...))
        UC->>UoW: commit()
        UoW->>DB: INSERT roles → COMMIT
        UoW->>UoW: AuditLoggingHandler.handle(RoleCreated)
        UoW->>DB: INSERT audit_logs → COMMIT
        Route-->>Admin: 201 RoleResponse
    end
```

---

## 7. Assign Permission to Role

```mermaid
sequenceDiagram
    participant Admin
    participant Route as rbac/routes.py
    participant UC as AssignPermissionUseCase
    participant UoW as SqlAlchemyRbacUnitOfWork
    participant DB as PostgreSQL

    Admin->>Route: POST /api/v1/admin/roles/{id}/permissions
    Route->>UC: execute(AssignPermissionInput)
    UC->>UoW: roles.find_by_id
    alt role not found
        UC-->>Route: raise RoleNotFoundError → 404
    else
        UC->>UoW: permissions.find_by_scope_key(ScopeKey)
        alt permission missing
            UC->>UoW: permissions.add(ScopeKey)
        end
        UC->>UoW: assignments.role_has_permission?
        alt already assigned
            UC-->>Route: raise PermissionAlreadyAssignedError → 409
        else
            UC->>UoW: assignments.assign_permission(role_id, perm_id, actor_id)
            UC->>UoW: add_event(PermissionGranted(...))
            UC->>UoW: commit()
            UoW->>DB: INSERT role_permissions → COMMIT
            UoW->>DB: INSERT audit_logs → COMMIT
            Route-->>Admin: 201 result
        end
    end
```

---

## 8. Get Audit Logs

```mermaid
sequenceDiagram
    participant Admin
    participant Route as audit/routes.py
    participant UC as GetAuditLogsUseCase
    participant Reader as SqlAlchemyAuditLogReader
    participant DB as PostgreSQL

    Admin->>Route: GET /api/v1/admin/audit-logs?page=1&page_size=20
    Route->>Route: require_super_user
    Route->>UC: execute(GetAuditLogsInput)
    UC->>Reader: list_paginated(page=1, page_size=20)
    Reader->>DB: SELECT audit_logs ORDER BY created_at DESC LIMIT 20 OFFSET 0
    DB-->>Reader: list[AuditLog]
    Reader-->>UC: list[AuditLog]
    UC-->>Route: GetAuditLogsResult
    Route-->>Admin: 200 [AuditLogResponse, ...]
```

---

## 9. JWKS Endpoint

```mermaid
sequenceDiagram
    participant Client
    participant Route as auth/jwks.py
    participant KeyPair as RSAKeyPair

    Client->>Route: GET /.well-known/jwks.json
    Route->>KeyPair: key_pair.public_key
    KeyPair-->>Route: RSA public key object
    Route->>Route: extract n, e via public_numbers()
    Route->>Route: base64url_encode(n), base64url_encode(e)
    Route->>Route: kid = SHA256(DER)[:16].base64url()
    Route-->>Client: 200 {"keys":[{kty:"RSA",use:"sig",kid,n,e}]}
```

---

## 10. Rate Limiting

```mermaid
sequenceDiagram
    participant Client
    participant RateLimit as rate_limit_by_ip
    participant Redis

    Client->>RateLimit: 1st request
    RateLimit->>Redis: INCR rate_limit:ip:{ip}:{path}
    Redis-->>RateLimit: 1
    RateLimit->>Redis: EXPIRE key 60s
    RateLimit-->>Client: continue

    Client->>RateLimit: 21st request within 60s
    RateLimit->>Redis: INCR key
    Redis-->>RateLimit: 21 (> 20 limit)
    RateLimit->>Redis: TTL key
    Redis-->>RateLimit: 45s remaining
    RateLimit-->>Client: 429 Too Many Requests (Retry-After: 45)
```
