# System Overview

Shop-Monorepo is an ecommerce backend platform composed of four Python microservices sharing a PostgreSQL cluster, Redis, and GCP Pub/Sub. Each service is independently deployable to GCP Cloud Run.

## Platform Map

```mermaid
graph TB
    subgraph Clients
        WEB[Web PWA<br/>Next.js]
        MOB[Mobile App]
        EXT[Third-party APIs]
    end

    subgraph GCP["GCP — Cloud Run"]
        IAM[iam-service<br/>:8000<br/>Auth · RBAC · Audit]
        CAT[catalog-service<br/>:8001<br/>Products · Categories]
        ORD[order-service<br/>:8002<br/>Orders · Payments]
        NOT[notification-service<br/>:8003<br/>Email · Push · SMS]
    end

    subgraph Data["GCP — Data Layer"]
        PG[(Cloud SQL<br/>PostgreSQL 17)]
        RDS[(Memorystore<br/>Redis 7)]
        PS[Pub/Sub<br/>Topics]
    end

    subgraph Secrets
        SM[Secret Manager]
    end

    WEB & MOB & EXT -->|HTTPS| IAM
    WEB & MOB & EXT -->|HTTPS + Bearer JWT| CAT
    WEB & MOB & EXT -->|HTTPS + Bearer JWT| ORD

    IAM --> PG
    IAM --> RDS
    CAT --> PG
    ORD --> PG
    ORD --> PS
    PS --> NOT

    SM -.->|env injection| IAM & CAT & ORD & NOT
```

## Responsibilities

| Service | Owns | Does NOT own |
|---------|------|--------------|
| **iam-service** | User identities, roles, permissions, audit log, token issuance | Business domain logic |
| **catalog-service** | Products, categories, inventory | Who can access them |
| **order-service** | Order lifecycle, payment events | Stock management |
| **notification-service** | Delivery of messages via channels | When or why to send them |

## Token Flow

Every protected endpoint in catalog and order services validates JWTs issued by iam-service using the public key served at `/.well-known/jwks.json`. No service-to-service credential exchange is needed.

```mermaid
sequenceDiagram
    participant Client
    participant IAM as iam-service
    participant CAT as catalog-service

    Client->>IAM: POST /api/v1/auth/login
    IAM-->>Client: access_token (RS256 JWT) + refresh_token cookie

    Client->>CAT: GET /products (Authorization: Bearer <token>)
    CAT->>IAM: GET /.well-known/jwks.json (cached)
    CAT->>CAT: verify RS256 signature locally
    CAT-->>Client: 200 products
```

## Local Development

All services start together via Docker Compose from the repo root:

```bash
docker-compose up
# postgres :5432 · redis :6379 · pubsub-emulator :8085
# iam :8000 · catalog :8001 · order :8002 · notification :8003
```

## Deployment

Each service has its own CI pipeline (`.github/workflows/<service>.yml`) that lints, tests, builds a Docker image, and deploys to Cloud Run on push to `main`.
