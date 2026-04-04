# System Architecture

## Overview

The Access Control Service follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────────┐
│                           API Layer (FastAPI)                       │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────────┐  │
│  │   /auth     │ │   /admin    │ │      /.well-known/          │  │
│  │  endpoints  │ │  endpoints  │ │        jwks.json            │  │
│  └─────────────┘ └─────────────┘ └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Service Layer                                │
│  ┌──────────────────┐                    ┌──────────────────────┐ │
│  │   AuthService    │                    │    RBACService       │ │
│  │  • signup()      │                    │  • create_role()     │ │
│  │  • login()       │                    │  • delete_role()     │ │
│  │  • refresh()     │                    │  • assign_permission │ │
│  │  • logout()      │                    │  • revoke_permission │ │
│  └──────────────────┘                    │  • assign_role_to_user│ │
│                                          │  • revoke_role_from_user│ │
│                                          │  • get_audit_logs()   │ │
│                                          └──────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Data Layer (SQLAlchemy)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │   User   │  │   Role   │  │Permission│  │    AuditLog       │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────────┘  │
│        │              │              │                               │
│        └──────┬───────┴──────┬──────┘                               │
│               └───────────────┘                                       │
│              Association Tables                                       │
│        (user_roles, role_permissions)                                │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     External Services                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐  │
│  │  PostgreSQL │  │    Redis    │  │        GCP Pub/Sub          │  │
│  │   (Cloud    │  │ (Memorystore│  │      (Activity Log)        │  │
│  │    SQL)     │  │    / Redis) │  │                           │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### API Layer (`app/api/v1/`)

- **File**: `auth.py` - Authentication endpoints
- **File**: `admin.py` - RBAC administrative endpoints
- **File**: `jwks.py` - JWKS endpoint for key discovery

**Responsibilities:**
- HTTP request/response handling
- Request validation using Pydantic schemas
- Dependency injection (current user, super user checks)
- Rate limiting (applied as dependencies)
- Setting response headers and cookies
- Mapping service exceptions to HTTP status codes

### Service Layer (`app/services/`)

- **File**: `auth_service.py` - `AuthService` class
- **File**: `rbac_service.py` - `RBACService` class

**Responsibilities:**
- Business logic implementation
- Database operations via SQLAlchemy
- Transaction management (commit responsibility typically on caller)
- Audit log creation for mutating operations
- Password hashing and verification
- JWT generation and validation
- Redis operations (refresh tokens, revocation)
- Domain-specific exception raising

### Data Layer (`app/models/`)

- **Files**: `user.py`, `role.py`, `association.py`, `audit_log.py`, `base.py`

**Responsibilities:**
- ORM model definitions with SQLAlchemy
- Table constraints (unique, foreign keys, indexes)
- Relationship definitions (many-to-many, one-to-many)
- Mixin inheritance for timestamps and soft deletes
- Database-agnostic schema definitions

### Core Utilities (`app/core/`)

- **Files**:
  - `security.py` - JWT operations, password hashing
  - `dependencies.py` - FastAPI dependencies (auth, super user)
  - `keys.py` - RSA key pair singleton
  - `rate_limit.py` - IP and username rate limiting
  - `loggin` - Structured JSON logging
  - `middleware.py` - Request ID middleware

**Responsibilities:**
- Cryptographic operations
- Dependency injection providers
- Singleton resource management
- Rate limiting algorithms
- Cross-cutting concerns (logging, request tracing)

### Database Layer (`app/db/`)

- **Files**: `session.py`, `redis.py`, `pubsub.py`

**Responsibilities:**
- Async PostgreSQL engine and session factory
- Redis client singleton
- GCP Pub/Sub client lazy initialization
- Connection lifecycle management
- Test database overrides

## Component Diagram

```mermaid
graph TB
    subgraph "Client Applications"
        WEB[Web Browser]
        MOBILE[Mobile App]
        API[Third-party API]
    end

    subgraph "Access Control Service"
        LB[Load Balancer]
        API1[FastAPI App]

        subgraph "API Layer"
            AUTH[auth endpoints]
            ADMIN[admin endpoints]
            JWKS[jwks json]
        end

        subgraph "Service Layer"
            AUTH_SVC[AuthService]
            RBAC_SVC[RBACService]
        end

        subgraph "Core Utilities"
            SEC[security.py]
            DEPS[dependencies.py]
            RATE[rate_limit.py]
            KEYS[keys.py]
        end

        subgraph "Data Models"
            USER[User]
            ROLE[Role]
            PERM[Permission]
            AUDIT[AuditLog]
            ASSOC[Association Tables]
        end
    end

    subgraph "External Services"
        PG[PostgreSQL]
        REDIS[Redis]
        PUBSUB[PubSub Topic]
    end

    WEB --> LB
    MOBILE --> LB
    API --> LB
    LB --> API1

    API1 --> AUTH
    API1 --> ADMIN
    API1 --> JWKS

    AUTH --> AUTH_SVC
    ADMIN --> RBAC_SVC

    AUTH_SVC --> SEC
    RBAC_SVC --> SEC

    AUTH_SVC --> DEPS
    ADMIN --> DEPS

    AUTH --> RATE
    ADMIN --> RATE

    AUTH_SVC --> USER
    RBAC_SVC --> ROLE
    RBAC_SVC --> PERM
    RBAC_SVC --> AUDIT
    AUTH_SVC --> ASSOC
    RBAC_SVC --> ASSOC

    AUTH_SVC --> PG
    RBAC_SVC --> PG
    AUTH_SVC --> REDIS
    DEPS --> REDIS

    AUTH_SVC --> PUBSUB

    style API1 fill:#007bb0
    style AUTH_SVC fill:#850099
    style RBAC_SVC fill:#850099
    style PG fill:#488701
    style REDIS fill:#8a002e
    style PUBSUB fill:#9c5d00
```

## Deployment Diagram

```mermaid
graph TB
    subgraph "Google Cloud Platform"
        subgraph "Load Balancing"
            LB[Cloud Load Balancer]
        end

        subgraph "Compute"
            CR[Cloud Run]
            subgraph "Service Instances"
                INST1[Instance 1]
                INST2[Instance 2]
                INST3[Instance N...]
            end
        end

        subgraph "Database"
            CS[Cloud SQL PostgreSQL]
        end

        subgraph "Cache"
            MS[Memorystore Redis]
        end

        subgraph "Messaging"
            PS[PubSub Topic]
        end

        subgraph "Secrets"
            SM[Secret Manager]
        end
    end

    subgraph "Development"
        LOCAL[Local Dev docker-compose]
    end

    LB --> CR
    CR --> INST1
    CR --> INST2
    CR --> INST3

    INST1 --> CS
    INST1 --> MS
    INST1 --> PS

    SM -.-> INST1

    LOCAL --> LB

    style LB fill:#007bb0
    style CR fill:#488701
    style CS fill:#488701
    style MS fill:#8a002e
    style PS fill:#9c5d00
    style SM fill:#850099
```

## Data Flow Patterns

### Authentication Flow

```
┌─────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────┐
│ Client  │────▶│   API    │────▶│ AuthService  │────▶│  Redis   │
│         │     │ (auth)   │     │              │     │          │
└─────────┘     └──────────┘     └──────────────┘     └──────────┘
     │                 │                    │                  │
     │                 │                    │                  │
     ▼                 ▼                    ▼                  ▼
┌─────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────┐
│ Response│◀────│  Token   │◀────│   JWT +      │◀────│ Refresh  │
│  + Cookies│   │Creation  │     │  Password    │     │  Token   │
│          │     │          │     │  Hash Check  │     │  Store   │
└─────────┘     └──────────┘     └──────────────┘     └──────────┘
                                                      
┌─────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────┐
│ Client  │────▶│   API    │────▶│ AuthService  │────▶│ PostgreSQL│
│         │     │ (signup) │     │              │     │          │
└─────────┘     └──────────┘     └──────────────┘     └──────────┘
     │                 │                    │                  │
     ▼                 ▼                    ▼                  ▼
┌─────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────┐
│  User   │◀────│  User    │◀────│   Create     │◀────│ INSERT   │
│ Created │     │  Record  │     │   User +     │     │  User    │
│         │     │          │     │   Viewer Role│     │          │
└─────────┘     └──────────┘     └──────────────┘     └──────────┘
```

### RBAC Administration Flow

```
┌─────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────┐
│ Super   │────▶│   API    │────▶│  RBACService │────▶│PostgreSQL│
│  User   │     │ (admin)  │     │              │     │          │
└─────────┘     └──────────┘     └──────────────┘     └──────────┘
     │                 │                    │                  │
     ▼                 ▼                    ▼                  ▼
┌─────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────┐
│ Role/   │◀────│  Create  │◀────│   Create     │◀────│ INSERT   │
│Permission│    │  Update  │     │   Role/Perm  │     │  Record  │
│ Modified│     │  Delete  │     │   or Assign  │     │          │
└─────────┘     └──────────┘     └──────────────┘     └──────────┘
                                    │
                                    ▼
                            ┌──────────────┐
                            │  AuditLog    │
                            │  Record      │
                            └──────────────┘
                                    │
                                    ▼
                            ┌──────────┐
                            │Pub/Sub   │
                            │(optional)│
                            └──────────┘
```

### Token Validation Flow

```
┌─────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────┐
│ Client  │────▶│   API    │────▶│ get_current_  │────▶│   Redis  │
│ with    │     │ Protected│     │    user       │     │          │
│  Token  │     │  Route   │     │ Dependency   │     │ (JTI     │
└─────────┘     └──────────┘     └──────────────┘     │ Revoke)  │
     │                 │                    │           └──────────┘
     ▼                 ▼                    ▼                  │
┌─────────┐     ┌──────────┐     ┌──────────────┐           │
│  Valid  │◀────│  Token   │◀────│  verify_      │◀──────────┘
│  Response│    │  Valid   │     │  access_token │     ┌──────────┐
│          │     │          │     │               │     │PostgreSQL│
└─────────┘     └──────────┘     └──────────────┘     │  (User   │
                                                       │  Load)   │
                                                       └──────────┘
```

## Interface Contracts

### Internal Interfaces

**Service ↔ Database**
- All database operations use SQLAlchemy Core/ORM
- Async sessions with `await` on all operations
- Connection pooling managed at engine level
- Transactions committed by caller (service methods don't auto-commit)

**Service ↔ Redis**
- `redis.asyncio` client for async operations
- Key patterns:
  - `refresh_token:{token}` → `user_id` (string)
  - `revoked_jti:{jti}` → `"1"` (set with expiry)
  - `rate_limit:ip:{ip}:{endpoint}` → counter (integer)
  - `rate_limit:username:{username}:{endpoint}` → counter (integer)

**Service → JWT**
- `security.create_access_token()` returns signed JWT string
- `security.verify_access_token()` returns payload dict or raises exception
- Uses RSA key pair from `core.keys.key_pair`

**API → Service**
- Direct method calls with Pydantic schema instances
- Service methods raise domain exceptions (see `core/exceptions.py`)
- API layer catches and converts to `HTTPException`

### External Interfaces

**Client → API**
- HTTPS REST API with JSON request/response bodies
- Authentication via `Authorization: Bearer <access_token>` header
- Refresh token via `refresh_token` httpOnly cookie (7-day expiry)
- All errors return JSON with `detail` field

**API → Disco`(Discovery)**
- JWKS endpoint at `/.well-known/jwk`s.json serves public key in JWK format
- Used by clients to validate JWT signatures

**Service → GCP Services**
- Pub/Sub publisher for async event delivery (not yet fully integrated)
- Cloud SQL via SQLAlchemy asyncpg driver
- Memorystore via Redis client

## Technology Choices & Rationale

### Why FastAPI?
- **Async-first**: Native support for async/await, critical for I/O-bound operations
- **Automatic docs**: OpenAPI/Swagger generated from code annotations
- **Pydantic v2**: Built-in request/response validation with modern typing
- **Performance**: On par with Node.js and Go in benchmarks
- **Type safety**: Full Python type hint support for IDE assistance

### Why SQLAlchemy 2.x async?
- Mature ORM with comprehensive feature set
- Full async support with `asyncpg` driver
- 2.0 style (futures) provides cleaner API than 1.4 style
- Migration path from existing Django ORM knowledge
- Alembic integration for schema migrations

### Why PyJWT over python-jose?
- Actively maintained (python-jose is deprecated)
- Better cryptography backend (`cryptography` library)
- More secure defaults
- Simpler API surface area

### Why Redis for token revocation?
- In-memory store provides O(1) lookup for JTI revocation checks
- TTL support ensures automatic cleanup of expired revoked tokens
- High performance under load
- GCP Memorystore provides managed Redis with HA

### Why RS256?
- Asymmetric cryptography: private key stays secret, public key distributed
- Supports key rotation via JWKS endpoint
- Industry standard for JWT signing (RFC 7518)
- Better security than HS256 (shared secret)

### Why bcrypt for passwords?
- Intentionally slow hashing algorithm resists brute force
- Adaptive work factor can be increased over time
- Widely industry standard
- `passlib` provides lazy migration from legacy schemes

### Why GCP Pub/Sub?
- Decouples event production from consumption
- Provides durable message storage
- Supports multiple subscribers (activity tracker, analytics, etc.)
- Scalable and managed service

## Non-Functional Characteristics

### Scalability
- **Horizontal Scaling**: Stateless API instances can be added behind load balancer
- **Database Connection Pool**: Configurable pool size (default 10) with overflow (default 20)
- **Redis Cluster**: Memorystore supports sharding for large datasets
- **Async I/O**: Single-threaded event loop handles thousands of concurrent connections

### Availability
- **99.95% Target**: Managed services (Cloud SQL HA, Memorystore, Pub/Sub) provide SLAs
- **Stateless Design**: Instances can be terminated and replaced without data loss
- **Graceful Shutdown**: Lifespan hooks ensure proper connection cleanup
- **Health Checks**: Startup verification of DB and Redis connectivity

### Security
- **Secrets Management**: All secrets injected via environment variables or GCP Secret Manager
- **Principle of Least Privilege**: Fine-grained permissions, super user required for admin ops
- **Defense in Depth**: Multiple security layers (network, application, data)
- **Encryption in Transit**: TLS for all external communications
- **Encryption at Rest**: Cloud SQL and Memorystore provide disk encryption

### Observability
- **Structured Logging**: JSON format with severity, request_id, timestamps
- **Request Tracing**: X-Request-ID header propagated through system
- **Metrics**: Ready for Prometheus/GCP Monitoring integration (middleware can be added)
- **Audit Trail**: All RBAC operations logged with actor, action, entity, payload

## Future Extensibility

### Planned Enhancements
1. Permission middleware (`@require_permission("resource:action")`)
2. Query-time soft delete filters (global query hooks)
3. GCP Secret Manager integration for production keys
4. Pub/Sub event publishing for all audit log entries
5. API versioning strategy (v2 endpoints)
6. OAuth2 social login integration
7. Multi-factor authentication (MFA)
8. Password reset flow
7. Email verification

### Extension Points
- New service classes can be added without modifying existing ones
- New API routers can be mounted at any prefix
- New model mixins can be created and inherited
- Additional Pydantic schemas can be defined for new use cases
- Rate limiting strategies can be swapped
- Logging handlers can be added for different destinations

## Dependencies

### Python Packages (from pyproject.toml)

```
fastapi>=0.110.0
uvicorn[standard]>=0.30.0
sqlalchemy>=2.0.0
alembic>=1.13.0
asyncpg>=0.29.0
redis>=5.0.0
pyjwt>=2.8.0
cryptography>=41.0.0
passlib[bcrypt]>=1.7.4
pydantic>=2.0.0
pydantic-settings>=2.0.0
httpx>=0.27.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
google-cloud-pubsub>=2.19.0
```

All dependencies managed by `uv` with locked versions in `uv.lock`.

## References

- `app/main.py` - Application factory and lifespan
- `app/config.py` - Configuration definitions
- `app/api/v1/` - API endpoint implementations
- `app/services/` - Business logic
- `app/models/` - Data models
- `app/core/` - Security and utilities
- `app/db/` - Database and external service connections
