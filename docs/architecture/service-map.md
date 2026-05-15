# IAM Service — Internal Map

The iam-service is structured as a hexagonal (ports & adapters) application with three bounded contexts. This document maps the internal components and their relationships.

## Bounded Context Layout

```mermaid
graph TB
    subgraph HTTP["HTTP Layer — FastAPI"]
        A_R[auth/routes.py<br/>POST signup · login · refresh · logout<br/>GET me]
        R_R[rbac/routes.py<br/>POST/DELETE roles · permissions · user-roles]
        AU_R[audit/routes.py<br/>GET audit-logs]
        JWKS[jwks.py<br/>GET /.well-known/jwks.json]
        DEP[dependencies.py<br/>get_current_user · require_super_user]
        RATE[rate_limit.py<br/>by IP · by username]
    end

    subgraph APP["Application Layer — Use Cases"]
        subgraph AUTH_UC["auth/"]
            SU[SignupUseCase]
            LU[LoginUseCase]
            RU[RefreshTokenUseCase]
            LO[LogoutUseCase]
        end
        subgraph RBAC_UC["rbac/"]
            CR[CreateRoleUseCase]
            DR[DeleteRoleUseCase]
            AP[AssignPermissionUseCase]
            RP[RevokePermissionUseCase]
            AR[AssignRoleToUserUseCase]
            RR[RevokeRoleFromUserUseCase]
        end
        subgraph AUDIT_UC["audit/"]
            GA[GetAuditLogsUseCase]
        end
    end

    subgraph DOM["Domain Layer — Ports & Entities"]
        subgraph SHARED_DOM["shared/domain/"]
            ENT[User · Role · Permission · AuditLog]
            VAL[Email · ScopeKey]
            EVT[DomainEvent base]
        end
        subgraph RBAC_DOM["rbac/domain/"]
            REVT[RoleCreated · RoleDeleted<br/>PermissionGranted · PermissionRevoked<br/>UserRoleAssigned · UserRoleRevoked]
            RPORTS[RoleRepository<br/>PermissionRepository<br/>AssignmentRepository<br/>RbacUnitOfWork]
        end
        subgraph AUTH_DOM["auth/domain/"]
            APORTS[UserRepository<br/>TokenIssuer · TokenVerifier<br/>PasswordHasher<br/>RefreshTokenStore · RevocationStore<br/>AuthUnitOfWork]
        end
    end

    subgraph INFRA["Infrastructure Layer — Adapters"]
        subgraph AUTH_INFRA["auth/infrastructure/"]
            ACOMP[composition.py — DI wiring]
            UREPO[SqlAlchemyUserRepository]
            UOWAL[SqlAlchemyAuthUnitOfWork]
            RTSTORE[RedisRefreshTokenStore]
            REVSTORE[RedisRevocationStore]
            KP[RSAKeyPair singleton]
            ISSUER[JwtTokenIssuer]
            VERIF[JwtTokenVerifier]
        end
        subgraph RBAC_INFRA["rbac/infrastructure/"]
            RCOMP[composition.py — DI wiring]
            RREPO[SqlAlchemyRoleRepository]
            PREPO[SqlAlchemyPermissionRepository]
            AREPO[SqlAlchemyAssignmentRepository]
            UOWR[SqlAlchemyRbacUnitOfWork<br/>+ event dispatch]
        end
        subgraph AUDIT_INFRA["audit/infrastructure/"]
            ALOGGER[SqlAlchemyAuditLogger]
            AREADER[SqlAlchemyAuditLogReader]
        end
        subgraph SHARED_INFRA["shared/infrastructure/"]
            HASHER[BcryptPasswordHasher]
            DB[AsyncSession / engine]
            REDIS[redis.asyncio client]
        end
    end

    subgraph EXT["External"]
        PG[(PostgreSQL)]
        CACHE[(Redis)]
    end

    HTTP --> APP
    APP --> DOM
    APP --> INFRA
    UOWR -->|injects| ALOGGER
    INFRA --> EXT
```

## Dependency Rules

```mermaid
flowchart LR
    INFRA[Infrastructure] -->|implements| DOM[Domain Ports]
    APP[Application] -->|depends on| DOM
    HTTP[HTTP / FastAPI] -->|calls| APP
    HTTP -->|injects via| COMP[composition.py]
    COMP -->|wires| INFRA

    DOM -.->|no dependency| INFRA
    DOM -.->|no dependency| HTTP
    APP -.->|no dependency| INFRA
    APP -.->|no dependency| HTTP
```

The domain layer has **zero** imports from FastAPI, SQLAlchemy, Redis, or PyJWT. All wiring happens in `composition.py` files using FastAPI `Depends`.

## Key Redis Key Patterns

| Key | Value | TTL |
|-----|-------|-----|
| `refresh_token:<token>` | `<user_id>` | 7 days |
| `revoked_jti:<jti>` | `"1"` | remaining access token lifetime |
| `rate_limit:ip:<ip>:<path>` | request count | 60 s |
| `rate_limit:username:<username>:<path>` | attempt count | 300 s |

## ORM Association Tables

```mermaid
erDiagram
    users {
        uuid id PK
        string username
        string email
        string password_hash
        bool is_super_user
        bool is_active
        bool is_deleted
    }
    roles {
        uuid id PK
        string name
        string description
        bool is_system
        uuid created_by FK
        bool is_deleted
    }
    permissions {
        uuid id PK
        string resource
        string action
        string scope_key
    }
    user_roles {
        uuid user_id FK
        uuid role_id FK
        uuid assigned_by FK
        datetime assigned_at
    }
    role_permissions {
        uuid role_id FK
        uuid permission_id FK
        uuid granted_by FK
        datetime granted_at
    }
    audit_logs {
        uuid id PK
        uuid actor_id FK
        string action
        string entity_type
        uuid entity_id
        json payload
        datetime created_at
    }

    users ||--o{ user_roles : ""
    roles ||--o{ user_roles : ""
    roles ||--o{ role_permissions : ""
    permissions ||--o{ role_permissions : ""
    users ||--o{ audit_logs : "actor"
```
