# Executive Summary

## Project Overview

The **Access Control Service** is a standalone microservice built with FastAPI (Python 3.13) that provides authentication, authorization, and identity management capabilities. It is a core component of a larger platform that was originally built with Django and has been migrated to a modern microservices architecture running on Google Cloud Platform (GCP).

### Migration Context

The service represents a strategic migration from a monolithic Django application to a microservices-based architecture. This migration was undertaken to improve scalability, maintainability, and operational independence of critical identity and access management functions. The current service is production-ready and deployed on GCP.

### Core Objectives

1. **Authentication via JWT using RS256**
   - Issue short-lived access tokens (15 minutes by default)
   - Issue long-lived refresh tokens (7 days) stored in httpOnly cookies
   - Use RS256 algorithm with RSA key pairs for signing
   - Support JWT revocation via JTI tracking in Redis

2. **Fine-Grained RBAC (Role-Based Access Control)**
   - Define permissions using `resource:action` scope keys
   - Assign roles to users via many-to-many relationships
   - Support hierarchical permission inheritance through roles
   - Provide super user capability for administrative override
   - Comprehensive audit logging for all RBAC operations

3. **Session Handling & Security**
   - Async Redis storage for refresh tokens and revoked JTIs
   - Rate limiting by IP (20 req/min) and username (5 failed logins/5min)
   - Password hashing with bcrypt, including lazy migration from Django's PBKDF2
   - Soft delete support for all main entities
   - Structured JSON logging for GCP Cloud Logging

## Target Audience

### For Developers
- API consumers integrating authentication into client applications
- Backend engineers extending the RBAC system
- DevOps engineers deploying and maintaining the service

### For Architects
- Understanding the microservice boundaries and integration patterns
- Evaluating security and scalability characteristics
- Planning infrastructure provisioning on GCP

### For Operations Teams
- Deployment and monitoring procedures
- Configuration management
- Troubleshooting common issues

## Technology Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Framework** | FastAPI | Latest | Async web framework with automatic OpenAPI docs |
| **Runtime** | Python | 3.13 | Modern Python with full async support |
| **ORM** | SQLAlchemy | 2.x (async) | Database access with async/await |
| **Migrations** | Alembic | Latest | Database schema versioning |
| **Validation** | Pydantic | v2 | Request/response validation and serialization |
| **Auth** | PyJWT + cryptography | Latest | JWT token creation and verification |
| **Password Hashing** | passlib/bcrypt | Latest | Secure password storage |
| **Cache/Session** | Redis (GCP Memorystore) | Latest | Refresh token storage, rate limiting, revocation |
| **Messaging** | GCP Pub/Sub | Latest | Asynchronous event publishing |
| **Database** | PostgreSQL (GCP Cloud SQL) | 15+ | Primary data persistence |
| **Package Manager** | uv | Latest | Fast dependency management |
| **Testing** | pytest + pytest-asyncio + httpx | Latest | Async testing framework |

## Key Features

### Authentication Flow
1. User signs up with username/password → account created, 'viewer' role assigned
2. User logs in → credentials verified, access + refresh tokens issued
3. Access token used for authorized API calls ( Bearer header )
4. Refresh token (cookie) used to obtain new access token when expired
5. Logout invalidates refresh token and revokes current access token

### Authorization System
1. Permissions defined as `resource:action` pairs (e.g., `users:read`, `roles:write`)
2. Roles group multiple permissions
3. Users assigned one or more roles
4. Super users bypass all permission checks
5. All admin operations (role/permission management) require super user status
6. Comprehensive audit logging for compliance

### Security Controls
- **JWT Signing**: RS256 with private key never exposed
- **Key Management**: RSA keys stored in GCP Secret Manager (production) or filesystem (dev)
- **Token Revocation**: JTI stored in Redis with TTL matching remaining token lifetime
- **Password Security**: bcrypt with automatic migration from legacy PBKDF2
- **Rate Limiting**: Per-IP and per-username to prevent brute force attacks
- **httponly Cookies**: Refresh tokens inaccessible to JavaScript
- **Input Validation**: Pydantic v2 schemas with strict typing
- **SQL Injection Prevention**: SQLAlchemy parameterized queries
- **XSS Protection**: SameSite cookies, httponly flags
- **Request Tracing**: X-Request-ID middleware for distributed tracing

## Project Structure

```
access-control-service/
├── app/
│   ├── api/v1/          # HTTP endpoints (auth, admin, jwks)
│   ├── core/            # Security, dependencies, rate limiting, utilities
│   ├── db/              # Database and Redis connections, Pub/Sub
│   ├── models/          # SQLAlchemy ORM models
│   ├── schemas/         # Pydantic request/response schemas
│   ├── services/        # Business logic layer
│   ├── config.py        # Settings configuration
│   └── main.py          # FastAPI app factory and lifespan
├── tests/
│   ├── conftest.py      # Shared fixtures
│   ├── unit/            # Unit tests (mock dependencies)
│   └── integration/     # Integration tests (real DB, mocked external)
├── keys/                # RSA key pair (dev only, .gitignored)
│   ├── private.pem
│   └── public.pem
├── alembic/             # Database migrations
├── .env.example         # Environment variable template
├── pyproject.toml       # Project dependencies and metadata
├── uv.lock              # Locked dependency versions
└── README.md            # Quick start guide
```

## Operational Characteristics

### Scalability
- **Stateless API Layer**: Multiple instances behind load balancer
- **Async I/O**: Handles high concurrency with minimal threads
- **Connection Pooling**: Configurable pool size for PostgreSQL
- **Redis Cluster**: Memorystore supports horizontal scaling
- **Pub/Sub**: Decoupled event publishing scales independently

### Availability
- **Lifespan Health Checks**: DB and Redis connectivity verified on startup
- **Graceful Shutdown**: Connections properly closed on termination
- **No Single Point of Failure**: Stateless design allows instance replacement
- **Cloud SQL HA**: Managed PostgreSQL with automated failover
- **Memorystore HA**: Managed Redis with replica support

### Observability
- **Structured Logging**: JSON format for Cloud Logging
- **Request Tracing**: X-Request-ID propagated through logs
- **Metric Collection**: Standard FastAPI metrics (via middleware potential)
- **Audit Trail**: Complete record of RBAC changes in `audit_logs` table

### Deployment Model

```
┌─────────────────┐
│   Load Balancer │
│   (GCP HTTP(S)) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐    ┌──────────────┐    ┌──────────┐
│   Service Inst  │────│   Cloud SQL  │    │ Memory   │
│   (Cloud Run)   │    │  (PostgreSQL)│    │ store    │
└─────────────────┘    └──────────────┘    └──────────┘
         │
         ▼
┌─────────────────┐
│   Pub/Sub Topic │
│  (Activity Log) │
└─────────────────┘
```

## Next Steps in This Documentation

The remainder of this documentation set covers:

1. **System Architecture**: Detailed component and deployment diagrams
2. **Component Details**: In-depth explanation of each layer
3. **API Contracts**: Complete endpoint specification with request/response schemas
4. **Data Models**: Database schema with ER diagram
5. **Security Architecture**: Cryptographic controls and threat model
6. **Configuration & Environment**: All settings and environment variables
7. **Deployment Guide**: Step-by-step setup for local and production
8. **Testing Strategy**: Unit, integration, and end-to-end testing approach
9. **Sequence Diagrams**: Visual flows for key operations
