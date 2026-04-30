# Security Architecture

## Threat Model Overview

| Threat | Mitigation |
|--------|------------|
| Credential theft | Bcrypt hashing, TLS, httponly cookies |
| Token replay | JTI revocation in Redis, short expiry |
| Brute force attacks | Rate limiting by IP and username |
| Privilege escalation | Super user check, role-based access control |
| SQL injection | SQLAlchemy parameterized queries |
| XSS | httponly, sameSite cookies, no inline scripts |
| CSRF | SameSite cookies, state-changing operations require POST/DELETE |
| Key compromise | RSA private key in GCP Secret Manager, rotation via JWKS |
| Session hijacking | Access token short TTL, refresh token rotation |

---

## JWT Handling

### Token Types

| Token | Purpose | Storage | Lifetime | Revocable |
|-------|---------|---------|----------|-----------|
| Access | API authentication | Client memory / Authorization header | 15 min | Yes (JTI in Redis) |
| Refresh | Obtain new access tokens | httpOnly cookie | 7 days | Yes (Redis key deletion) |

### Access Token

**Format**: JSON Web Token (JWT) with RS256 signature

**Header**:
```json
{
  "alg": "RS256",
  "typ": "JWT",
  "kid": "a1b2c3d4e5f67890"  // key identifier
}
```

**Payload Claims** (`app/auth/infrastructure/crypto/jwt_token_issuer.py`):

| Claim | Type | Description |
|-------|------|-------------|
| `sub` | string | User ID (UUID as string) |
| `iss` | string | Issuer ("access-control-service") |
| `iat` | integer | Issued at timestamp (seconds since epoch) |
| `exp` | integer | Expiration timestamp |
| `jti` | string | JWT ID (UUID4 string) for revocation |
| `username` | string | Username |
| `roles` | array[string] | List of role names |
| `permissions` | array[string] | List of permission scope keys |
| `is_super_user` | boolean | Admin override flag |

**Example**:
```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "iss": "access-control-service",
  "iat": 1736934600,
  "exp": 1736935500,
  "jti": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "username": "johndoe",
  "roles": ["viewer", "editor"],
  "permissions": ["users:read", "posts:write"],
  "is_super_user": false
}
```

**Signing** (`app/shared/infrastructure/crypto/jwt_token_issuer.py`): `JwtTokenIssuer.issue(TokenClaims)` — builds payload with all claims, signs with RS256 private key via PyJWT.

**Validation** (`app/shared/infrastructure/crypto/jwt_token_verifier.py`): `JwtTokenVerifier.verify(token)` — decodes with RS256 public key, requires `exp`, `sub`, `jti`, `iss`. Raises `TokenExpiredError` or `InvalidTokenError` (both in `app/auth/domain/exceptions.py`).

---

### JTI Revocation

**Purpose**: Allow immediate invalidation of access tokens before expiry (e.g., logout, compromise).

**Storage**: Redis key-value store

**Pattern**:
- On logout (`LogoutUseCase`): `revocation_store.revoke(jti, remaining_ttl)` → `RedisRevocationStore` calls `SETEX revoked_jti:{jti}`
- On each request (`get_current_user` in `app/auth/infrastructure/http/dependencies.py`): `revocation_store.is_revoked(jti)` → raises `HTTPException(401)` if found

**TTL**: Matches remaining token lifetime; Redis auto-evicts expired keys.

**Scale**: Redis `SETEX` and `GET` are O(1) operations; suitable for high-scale revocation checking.

---

### Refresh Token

**Generation**: `secrets.token_urlsafe(64)` (512 bits of entropy)

**Storage**: httpOnly cookie named `refresh_token`

**Redis Mapping**:
```
Key: refresh_token:<token_string>
Value: <user_id>
TTL: 7 days (configurable)
```

**Rotation**:
1. Client sends refresh token (cookie)
2. Server validates exists in Redis
3. Server generates NEW refresh token
4. Server deletes old key: `redis_client.delete(old_token_key)`
5. Server stores new mapping: `redis_client.setex(new_token_key, ttl, user_id)`
6. Server returns new access token and sets new refresh cookie

**Security Benefits**:
- Stolen refresh token can only be used once (rotation invalidates previous)
- Server can revoke all tokens by deleting Redis key family on compromise
- Refresh token is never exposed to JavaScript (httponly)

---

## Cryptographic Controls

### RSA Key Pair

**Algorithm**: RSA (2048-bit or 4096-bit recommended)

**Storage**:
- Development: Filesystem (`keys/private.pem`, `keys/public.pem`) - **NOT COMMITTED**
- Production: GCP Secret Manager

**Loading** (`app/auth/infrastructure/crypto/key_pair.py`): `RSAKeyPair` singleton; `load()` reads PEM files via `cryptography` library. Called once during app lifespan startup.

**Key Format**: PEM-encoded RSA keys (PKCS#1 or PKCS#8)

**Generation** (OpenSSL):
```bash
openssl genrsa -out keys/private.pem 2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem
```

**Rotation**:
1. Generate new key pair
2. Add new public key to JWKS endpoint (new `kid`)
3. Keep old private key for verifying existing tokens until they expire
4. Update service to load both keys, select by `kid` in JWT header
5. After all tokens signed with old key expire, remove old key

**Current Implementation**: Single key pair; does not support multiple active keys for rotation. JWKS `kid` is derived from public key hash but only one key is served.

---

## Password Security

### Bcrypt Hashing

**Library**: `passlib` with `bcrypt` scheme

**Work Factor**: Default rounds (typically 12, depends on `passlib` defaults)

**Implementation** (`app/shared/infrastructure/crypto/bcrypt_password_hasher.py`): `BcryptPasswordHasher` wraps `passlib.CryptContext(schemes=["bcrypt", "django_pbkdf2_sha256"], deprecated="auto")`. Implements the `PasswordHasher` port.

**Lazy Migration from Django PBKDF2**: `LoginUseCase` calls `hasher.needs_rehash(hash)` and if `True`, re-hashes the plain password with bcrypt and persists it in the same UoW transaction.

**Workflow**:
1. User signs up with Django (legacy) → password stored as PBKDF2 hash
2. On first login to new service:
   - `verify_password()` identifies scheme as deprecated
   - `needs_rehash()` returns True
   - Hash upgraded to bcrypt on login, saved to DB
3. Future logins use bcrypt

**Password Complexity Requirements** (`app/schemas/auth.py:39-77`):
- Minimum length: 8 characters
- At least one uppercase letter: `[A-Z]`
- At least one digit: `[0-9]`
- At least one special character: `!@#$%^&*()_+-=[]{}|;':",<>,./?`

**Validator**:
```python
@field_validator("password")
@classmethod
def validate_password(cls, v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;':\",<>,./?]", v):
        raise ValueError("Password must contain at least one special character")
    return v
```

---

## Rate Limiting

### IP-Based Rate Limiting

**Threshold**: 20 requests per 60 seconds per IP address

**Endpoints** (`app/api/v1/auth.py:14,71,121,169,195`):
- `POST /auth/signup`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`

**Implementation** (`app/shared/infrastructure/http/rate_limit.py`): `rate_limit_by_ip` — Redis `INCR rate_limit:ip:{ip}:{path}`, sets `EXPIRE 60` on first request, raises `HTTPException(429)` with `Retry-After` header when over 20.

**Response**: `429 Too Many Requests` with `Retry-After` header (seconds until reset)

---

### Username-Based Rate Limiting

**Threshold**: 5 attempts per 300 seconds (5 minutes) per username

**Endpoints**: Only `POST /auth/login`

**Implementation** (`app/core/rate_limit.py:41-70`):
```python
body = await request.body()
data = json.loads(body) if body else {}
username = data.get("username", "").strip().lower()
if username:
    key = f"rate_limit:username:{username}:{request.url.path}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, USERNAME_WINDOW)  # 300 seconds
    if count > USERNAME_MAX_ATTEMPTS:  # 5
        raise HTTPException(429, "Too many attempts")
```

**Purpose**: Thwart credential stuffing and username enumeration attacks.

---

## Token Lifecycle Management

### Access Token Lifecycle

1. **Issuance**: `AuthService.login()` or `refresh_token()`
2. **Validation**: `get_current_user()` dependency checks signature, expiry, JTI revocation
3. **Expiration**: 15 minutes (configurable via `jwt_access_token_expire_minutes`)
4. **Revocation**: Logout or refresh rotates token; JTI stored in Redis with TTL = remaining lifetime

### Refresh Token Lifecycle

1. **Issuance**: `AuthService.login()` or `refresh_token()`; sent as httpOnly cookie
2. **Storage**: Redis mapping `refresh_token:{token}` → `user_id` (7-day TTL)
3. **Rotation**: On refresh, old token deleted, new issued
4. **Revocation**: On logout, delete from Redis
5. **Expiration**: 7 days (configurable); automatic Redis expiry

### Cookie Settings

```python
# FastAPI Response.set_cookie() call
response.set_cookie(
    key="refresh_token",
    value=refresh_token,
    httponly=True,
    secure=settings.app_env == "production",  # HTTPS only in prod
    samesite="lax",
    max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
    path="/",
)
```

**Security Flags**:
- `HttpOnly`: Prevents JavaScript access (XSS protection)
- `Secure`: Only sent over HTTPS (enforced in production)
- `SameSite=Lax`: Protects against CSRF; sent with same-site navigation and top-level GETs

---

## Dependency Injection Security

### `get_current_user` Dependency

**File**: `app/core/dependencies.py:14-45`

**Flow**:
1. Extract `Authorization: Bearer <token>` header
2. Call `security.verify_access_token(token)` - validates signature, expiry, issuer
3. Extract `jti` from payload
4. Check Redis for `revoked_jti:{jti}` - raises 401 if found
5. Return `TokenPayload` TypedDict for downstream dependencies

**TokenPayload Definition** (`app/core/types.py`):
```python
class TokenPayload(TypedDict):
    sub: str
    username: str
    roles: list[str]
    permissions: list[str]
    is_super_user: bool
    exp: int
    iat: int
    jti: str
```

### `require_super_user` Dependency

**File**: `app/core/dependencies.py:48-66`

**Flow**:
1. Accept `TokenPayload` from `get_current_user`
2. Check `payload["is_super_user"]` is True
3. Raise `403 Forbidden` if False
4. Return payload unchanged

**Application**: Admin endpoints use `dependencies=[Depends(require_super_user)]`

---

## Input Validation

### Pydantic v2 Schemas

All request bodies validated using Pydantic schemas with strict typing.

**Examples**:

```python
class SignupRequest(BaseModel):
    username: str  # Constraints: min_length=3, max_length=50
    password: str  # Custom validator for complexity
    email: EmailStr | None = None
```

**Benefits**:
- Type safety and data coercion
- Clear error messages (422 response with details)
- Automatic OpenAPI schema generation
- Protection against malformed input

---

## Secrets Management

### Environment Variables (`.env`)

Never commit secrets. Use `.env` locally (gitignored) and GCP Secret Manager in production.

**Required**:
```
DATABASE_URL=postgresql+asyncpg://...
REDIS_URL=redis://...
RSA_PRIVATE_KEY_PATH=keys/private.pem
RSA_PUBLIC_KEY_PATH=keys/public.pem
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

**Optional**:
```
APP_ENV=development
APP_DEBUG=true
LOG_LEVEL=INFO
```

### GCP Secret Manager (Production)

Recommended configuration:
- Secret name: `access-control-service-rsa-private-key` (PEM format)
- Secret name: `access-control-service-rsa-public-key`
- Service account permissions: `secretmanager.secrets.access`
- Load at application startup via `google-cloud-secret-manager` library

Current implementation reads from filesystem paths; production should override `load()` method to fetch from Secret Manager instead.

---

## Audit Logging

### What Gets Logged

All RBAC administrative operations (`app/services/rbac_service.py:_write_audit_log`):

- `ROLE_CREATED`
- `ROLE_DELETED`
- `PERMISSION_GRANTED`
- `PERMISSION_REVOKED`
- `USER_ROLE_ASSIGNED`
- `USER_ROLE_REVOKED`

### Audit Log Schema

```python
class AuditLog(Base):  # app/models/audit_log.py
    id = Column(UUID, primary_key=True, server_default=gen_random_uuid())
    actor_id = Column(UUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(255), nullable=False)
    entity_type = Column(String(255), nullable=False)
    entity_id = Column(UUID, nullable=True)
    payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**Payload Examples**:
- Role created: `{"name": "editor", "description": "Can edit content"}`
- Permission granted: `{"role_id": "...", "permission_scope": "users:read"}`
- Role assigned to user: `{"user_id": "...", "role_id": "..."}`

### Audit Trail Integrity

- Audit logs are **immutable** (no `is_deleted` column)
- Stored in PostgreSQL with `created_at` auto-set
- `actor_id` from authenticated user's `sub` claim
- Payload stored as `JSONB` for flexible structure and queryability

---

## SQL Injection Prevention

All database access uses SQLAlchemy ORM or Core with parameterized queries:

```python
# Safe - parameterized
stmt = select(User).where(User.username == username)

# NOT ALLOWED - raw string concatenation (never done)
# stmt = text(f"SELECT * FROM users WHERE username = '{username}'")
```

SQLAlchemy automatically escapes parameters; no direct string interpolation.

---

## HTTPS & Network Security

### In Transit
- All external API traffic must use HTTPS
- Load balancer terminates TLS
- Internal traffic between service instances and Cloud SQL/Memorystore uses Google's private network (encrypted by default)

### At Rest
- Cloud SQL: Automatic encryption at rest
- Memorystore: Encryption at rest (depends on tier)
- Secrets in Secret Manager: Encrypted with Cloud KMS

---

## Security Checklist

- [x] JWT signed with RS256 (asymmetric)
- [x] Access token short TTL (15 min)
- [x] Refresh token httpOnly cookie
- [x] Refresh token rotation
- [x] JTI revocation in Redis
- [x] Bcrypt password hashing
- [x] Lazy migration from legacy hashes
- [x] Rate limiting (IP and username)
- [x] Super user required for admin endpoints
- [x] Pydantic input validation
- [x] SQL injection prevention via ORM
- [x] httponly + SameSite cookies
- [x] Audit logging for RBAC changes
- [ ] Global query filter for soft deletes (potential improvement)
- [ ] Key rotation with multiple JWKS (future enhancement)
- [ ] Content Security Policy headers (could be added)
- [ ] Request logging of auth failures for intrusion detection
- [ ] IP allowlist for admin endpoints (could be added)

---

## References

- JWT creation/validation: `app/core/security.py:33-81`
- Token revocation: `app/services/auth_service.py:243-269`
- Refresh token rotation: `app/services/auth_service.py:180-240`
- Password hashing: `app/core/security.py:13-30`
- Rate limiting: `app/core/rate_limit.py`
- Authentication dependency: `app/core/dependencies.py:14-45`
- Super user check: `app/core/dependencies.py:48-66`
- Audit logging: `app/services/rbac_service.py:_write_audit_log`
- RSA keys: `app/core/keys.py`
