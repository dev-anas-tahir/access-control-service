# Deployment Guide

## Local Development Setup

### Prerequisites

- **Python 3.13** or later (use `pyenv` or system Python)
- **uv** package manager (`pip install uv` or install from [astral.sh/uv](https://astral.sh/uv))
- **Docker** and **Docker Compose** (for PostgreSQL and Redis)
- **OpenSSL** (for generating RSA keys)

---

### Step 1: Clone and Install

```bash
cd /path/to/access-control-service
uv sync  # Installs dependencies from pyproject.toml into .venv
```

**uv Commands**:
- `uv run <command>`: Execute command with project's virtual environment
- `uv add <package>`: Add dependency to pyproject.toml

---

### Step 2: Start Infrastructure with Docker Compose

Create `docker-compose.yml` (if not present):

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: access_control_dev
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

Start services:
```bash
docker compose up -d postgres redis
```

Verify:
```bash
docker compose ps
docker compose logs postgres
docker compose logs redis
```

---

### Step 3: Generate RSA Key Pair

```bash
mkdir -p keys
openssl genrsa -out keys/private_key.pem 2048
openssl rsa -in keys/private_key.pem -pubout -out keys/public.pem

# Verify:
ls -la keys/
# -rw-r--r--  2 keys/private_key.pem
# -rw-r--r--  2 keys/public.pem
```

Set permissions:
```bash
chmod 600 keys/private_key.pem
chmod 644 keys/public.pem
```

**Important**: `keys/` directory is gitignored. Never commit private key.

---

### Step 4: Create `.env` File

```ini
# .env
app_env=development
app_debug=true
log_level=DEBUG

database_url=postgresql+asyncpg://postgres:postgres@localhost:5432/access_control_dev
redis_url=redis://localhost:6379/0

private_key_path=keys/private_key.pem
public_key_path=keys/public.pem

gcp_project_id=dummy-project
pubsub_topic_id=dummy-topic
```

**Test connection**:
```bash
uv run python -c "from app.config import settings; print(settings.database_url)"
```

---

### Step 5: Initialize Database

Generate and apply Alembic migrations:

```bash
# If migrations exist:
uv run alembic upgrade head

# If starting from scratch with no migrations:
uv run alembic revision --autogenerate -m "initial schema"
uv run alembic upgrade head
```

**Check schema**:
```bash
docker exec -it <postgres_container> psql -U postgres -d access_control_dev -c "\dt"
```

Expected tables:
- `users`
- `roles`
- `permissions`
- `user_roles`
- `role_permissions`
- `audit_logs`

---

### Step 6: Seed Default Data

The 'viewer' role must exist for signup to work.

Create seed script (`scripts/seed.py`):
```python
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_session_factory
from app.models.role import Role

async def seed():
    async with async_session_factory() as session:
        # Check if viewer role exists
        result = await session.execute(
            select(Role).where(Role.name == "viewer", Role.is_deleted == False)
        )
        if result.scalar_one_or_none() is None:
            viewer = Role(
                name="viewer",
                description="Default read-only role",
                is_system=True
            )
            session.add(viewer)
            await session.commit()
            print("Created 'viewer' role")
        else:
            print("'viewer' role already exists")

if __name__ == "__main__":
    asyncio.run(seed())
```

Run:
```bash
uv run python scripts/seed.py
```

**Optional**: Create initial super user:
```python
from app.services.auth_service import AuthService
from app.schemas.auth import SignupRequest

async def create_superuser():
    async with async_session_factory() as session:
        data = SignupRequest(
            username="admin",
            password="AdminPass123!",
            email="admin@example.com"
        )
        user = await AuthService.signup(session, data)
        # Set super user
        user.is_super_user = True
        await session.commit()
        print(f"Super user created: {user.username}")
```

---

### Step 7: Run the Development Server

```bash
uvicorn app.main:app --reload --port 8000
```

**Output**:
```
INFO:     Will watch for changes in these directories: ['/path/to/app']
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Open interactive API docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## GCP Production Deployment

### Architecture

```mermaid
---
config:
  theme: 'dark'
---
flowchart TD
    LB["Load Balancer<br>(GCP HTTP(S))"]
    SI["Service Instance<br>(Cloud Run)"]
    CS@{ shape: cyl, label: "Cloud SQL<br>(PostgreSQL)" }
    MS@{ shape: cyl, label: "Memory Store" }
    PS["Pub/Sub Topic<br>(Activity Log)"]

    LB --> SI
    SI --> CS
    SI --> MS
    SI --> PS
```

---

### Step 1: Set Up GCP Resources

1. **Create GCP Project**:
   ```bash
   gcloud projects create access-control-prod --name="Access Control Service"
   gcloud config set project access-control-prod
   ```

2. **Enable APIs**:
   ```bash
   gcloud services enable \
     cloudbuild.googleapis.com \
     run.googleapis.com \
     sqladmin.googleapis.com \
     redis.googleapis.com \
     pubsub.googleapis.com \
     secretmanager.googleapis.com
   ```

3. **Create Cloud SQL PostgreSQL Instance**:
   ```bash
   gcloud sql instances create access-control-db \
     --database-version=POSTGRES_15 \
     --tier=db-f1-micro \
     --region=us-central1 \
     --root-password=change-me-in-production \
     --storage-type=SSD
   ```

   Create database:
   ```bash
   gcloud sql databases create access_control --instance=access-control-db
   ```

   Get connection string:
   ```bash
   gcloud sql instances describe access-control-db --format="value(ipAddresses.ipAddress)"
   # Cloud SQL Auth proxy recommended; see below
   ```

4. **Create Memorystore Redis Instance**:
   ```bash
   gcloud redis instances create access-control-redis \
     --size=1 \
     --region=us-central1 \
     --redis-version=redis_7_0
   ```

   Get connection endpoint:
   ```bash
   gcloud redis instances describe access-control-redis --region=us-central1 \
     --format="value(host)"
   ```

5. **Create Pub/Sub Topic**:
   ```bash
   gcloud pubsub topics create access-control-activity
   ```

6. **Create RSA Key Pair in Secret Manager**:
   ```bash
   # Generate keys locally (or on secure machine)
   openssl genrsa -out private.pem 2048
   openssl rsa -in private.pem -pubout -out public.pem

   # Create secrets
   echo "$(cat private.pem)" | gcloud secrets create jwt-private-key \
     --replication-policy="automatic" \
     --data-file=-

   echo "$(cat public.pem)" | gcloud secrets create jwt-public-key \
     --replication-policy="automatic" \
     --data-file=-
   ```

7. **Grant Cloud Run Service Account Access to Secrets**:
   ```bash
   PROJECT_NUMBER=$(gcloud projects describe $GOOGLE_CLOUD_PROJECT --format="value(projectNumber)")
   SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

   gcloud secrets add-iam-policy-binding jwt-private-key \
     --member="serviceAccount:${SERVICE_ACCOUNT}" \
     --role="roles/secretmanager.secretAccessor"

   gcloud secrets add-iam-policy-binding jwt-public-key \
     --member="serviceAccount:${SERVICE_ACCOUNT}" \
     --role="roles/secretmanager.secretAccessor"
   ```

8. **Grant Cloud Run Service Account Access to Cloud SQL**:
   ```bash
   gcloud sql instances add-iam-policy-binding access-control-db \
     --member="serviceAccount:${SERVICE_ACCOUNT}" \
     --role="roles/cloudsql.client"
   ```

---

### Step 2: Configure Build and Deploy

**`Dockerfile`** (if not present, add one):

```dockerfile
# Dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies (if any)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install uv and dependencies
RUN pip install uv
RUN uv sync --system --no-dev  # Install to system Python, skip dev deps

# Copy application code
COPY app/ ./app/

# Run as non-root user
RUN useradd --create-home appuser
USER appuser

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

Build and push to Artifact Registry:

```bash
gcloud artifacts repositories create access-control-repo \
  --repository-format=docker \
  --location=us-central1 \
  --description="Access Control Service container images"

# Configure Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build
docker build -t us-central1-docker.pkg.dev/$GOOGLE_CLOUD_PROJECT/access-control-repo/access-control:latest .

# Push
docker push us-central1-docker.pkg.dev/$GOOGLE_CLOUD_PROJECT/access-control-repo/access-control:latest
```

---

### Step 3: Deploy to Cloud Run

```bash
gcloud run deploy access-control-service \
  --image=us-central1-docker.pkg.dev/$GOOGLE_CLOUD_PROJECT/access-control-repo/access-control:latest \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated=false \  # Require authentication; use IAM or custom auth
  --set-secrets="/secrets/jwt-private.pem=jwt-private-key:latest" \
  --set-secrets="/secrets/jwt-public.pem=jwt-public-key:latest" \
  --set-env-vars="APP_ENV=production" \
  --set-env-vars="DATABASE_URL=postgresql+asyncpg://..." \
  --set-env-vars="REDIS_URL=rediss://..." \
  --set-env-vars="GCP_PROJECT_ID=$GOOGLE_CLOUD_PROJECT" \
  --set-env-vars="PUBSUB_TOPIC_ID=access-control-activity" \
  --vpc-connector=projects/$GOOGLE_CLOUD_PROJECT/locations/us-central1/connectors/access-control-vpc \
  --cpu=1 \
  --memory=512Mi \
  --min-instances=1 \
  --max-instances=10
```

**Notes**:
- `--allow-unauthenticated=false` requires IAM for access; API Gateway or Cloud Endpoints recommended for public APIs
- Use VPC connector for private IP connectivity to Cloud SQL and Memorystore (avoid public IPs)
- Secrets mounted as files at `/secrets/jwt-private.pem` and `/secrets/jwt-public.pem`
- Alternatively, use Secret Manager directly in app code (recommended)

---

### Step 4: Configure Load Balancer

For public API access, create serverless NEG and external HTTP(S) load balancer:

```bash
# Create serverless NEG
gcloud compute network-endpoint-groups create access-control-neg \
  --region=us-central1 \
  --cloud-run-service=access-control-service

# Create backend service
gcloud compute backend-services create access-control-backend \
  --global \
  --protocol=HTTP \
  --port-name=http

# Add NEG to backend
gcloud compute backend-services add-backend access-control-backend \
  --global \
  --network-endpoint-group=access-control-neg \
  --network-endpoint-group-region=us-central1

# Create URL map
gcloud compute url-maps create access-control-urlmap \
  --default-service=access-control-backend

# Create target HTTP proxy and forwarding rule (with SSL cert)
# See: https://cloud.google.com/load-balancing/docs/https/setting-up-https-serverless
```

Alternatively, use **API Gateway** for full API management (quota, auth, monitoring).

---

## Health Checks

### Liveness Probe

FastAPI `/health` endpoint recommended for Cloud Run health checks.

Add to `app/api/v1/health.py`:

```python
from fastapi import APIRouter, Depends
from app.db.session import get_db

router = APIRouter()

@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    # Simple DB check also verifies Redis via liveness
    await db.execute(text("SELECT 1"))
    return {"status": "healthy"}
```

Configure Cloud Run health check:
```bash
gcloud run services update access-control-service \
  --health-check-path=/api/v1/health
```

---

## Monitoring & Logging

### GCP Cloud Logging

- All logs from Cloud Run automatically sent to Cloud Logging in JSON format
- Structured logs (`app/core/logging.py`) parsed by Cloud Logging agent
- View logs: `gcloud logging read "resource.type=cloud_run_revision AND resource.service.name=access-control-service"`

### Custom Metrics

Add Prometheus or OpenTelemetry instrumentation:

```python
from prometheus_client import Counter, Histogram

http_requests_total = Counter("http_requests_total", "Total HTTP requests", ["method", "path", "status"])
http_request_duration = Histogram("http_request_duration_seconds", "HTTP request duration", ["method", "path"])

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    http_requests_total.labels(request.method, request.url.path, response.status_code).inc()
    http_request_duration.labels(request.method, request.url.path).observe(duration)
    return response
```

---

### Alerts

Set up Cloud Monitoring alerts:

- **Error rate > 5%** over 5 minutes
- **Latency p95 > 500ms**
- **Pub/Sub backlog > 1000** messages
- **Database connections > 80%** of pool limit
- **Redis memory usage > 85%**

Use Cloud Monitoring alerting policies.

---

## Backup and Disaster Recovery

### Database Backups

Cloud SQL automated backups:
- Enabled by default (daily)
- 7-day retention (configurable)
- Point-in-time recovery enabled

Manual backup:
```bash
gcloud sql backups create --instance=access-control-db
```

### Redis Backups

Memorystore does not support automated backups (ephemeral cache). If persistence required, consider:
- Using Cloud SQL for session storage instead
- Implementing periodic RDB snapshots to Cloud Storage (custom solution)
- Reconstitute cache from source of truth (DB) on restart

### Key Backup

RSA private key stored in Secret Manager with versions. Enable secret replication across regions for disaster recovery.

---

## Scaling Considerations

### Horizontal Scaling

- **Cloud Run**: Auto-scales based on request rate (concurrency = 1 by default; can increase to 4-8 for better throughput)
- **Database**: Connection pool sizing critical; max connections per instance = `pool_size + max_overflow`; total connections = `instances * per_instance_limit`
- **Redis**: Memorystore cluster can handle 10k+ ops/sec; monitor CPU and memory

**Example**: 10 Cloud Run instances with pool_size=10, max_overflow=20 → 300 connections to Cloud SQL.

Adjust Cloud SQL `max_connections` accordingly (default 100, may need increase).

---

### Vertical Scaling

- **Cloud Run**: Increase CPU and memory allocation
- **Cloud SQL**: Change machine type (db-custom-2-4096, etc.)
- **Memorystore**: Increase memory size

---

## Security Hardening

### IAM Roles (Principle of Least Privilege)

**Cloud Run Service Account**:
- `roles/cloudsql.client` (for Cloud SQL connection)
- `roles/secretmanager.secretAccessor` (for RSA keys)
- `roles/pubsub.publisher` (for activity logging)
- `roles/logging.logWriter` (Cloud Run includes this by default)

**Developer Access**:
- `roles/run.admin` (deploy)
- `roles/cloudsql.editor` (dev DB access)
- `roles/secretmanager.viewer` and `secretAccessor` (view and access)

### Network Security

- Use **VPC Connector** for private IP connectivity to Cloud SQL and Memorystore (avoid public IP exposure)
- Configure **EGRESS settings** to control outbound traffic
- Enable **Binary Authorization** for container image attestation (optional)

### Database Security

- Use Cloud SQL IAM database authentication (instead of passwords)
- Encrypt connections (SSL/TLS)
- Rotate passwords periodically (or use IAM)
- Enable automated vulnerability scanning

---

## Deployment Checklist

**Pre-Deployment**:
- [ ] All tests passing: `uv run pytest --cov=app`
- [ ] Linting: `ruff check .` and `ruff format .`
- [ ] Migrations generated and reviewed
- [ ] Docker image built and scanned for vulnerabilities
- [ ] Environment variables configured in Cloud Run
- [ ] Secrets loaded in Secret Manager
- [ ] Service account IAM roles assigned
- [ ] VPC connector created (if using private IP)

**Deployment**:
- [ ] Deploy to staging environment first
- [ ] Run integration tests against staging
- [ ] Verify health endpoint returns 200
- [ ] Check logs for startup errors
- [ ] Test signup/login flow
- [ ] Test admin RBAC operations
- [ ] Verify JWKS endpoint accessible
- [ ] Configure load balancer/API Gateway
- [ ] Update DNS (if applicable)

**Post-Deployment**:
- [ ] Monitor error rate in Cloud Monitoring
- [ ] Set up alerts
- [ ] Document deployment version
- [ ] Backup database
- [ ] Perform security scan

---

## Rolling Back

**Cloud Run**:
```bash
gcloud run services update-accessibility access-control-service \
  --no-allow-unauthenticated  # Disable traffic
# Or roll back to previous revision:
gcloud run services update access-control-service \
  --revision-suffix=old
```

**Database**:
```bash
gcloud sql backups restore --backup-id=<backup_id> --instance=access-control-db
```

---

## CI/CD Pipeline (GitHub Actions Example)

`.github/workflows/deploy.yml`:

```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv sync --frozen
      - name: Run tests
        run: uv run pytest --cov=app

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and push
        run: |
          docker build -t gcr.io/${{ secrets.GCP_PROJECT }}/access-control:${{ github.sha }} .
          echo ${{ secrets.GCP_SA_KEY }} | gcloud auth activate-service-account --key-file=-
          docker push gcr.io/${{ secrets.GCP_PROJECT }}/access-control:${{ github.sha }}

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy access-control-service \
            --image=gcr.io/${{ secrets.GCP_PROJECT }}/access-control:${{ github.sha }} \
            --region=us-central1 \
            --platform=managed \
            --set-env-vars="APP_ENV=production" ...
```

---

## References

- Lok: `app/main.py` (startup verification, lifespan)
- Config: `app/config.py` (all settings)
- Database: `app/db/session.py` (connection pooling)
- Redis: `app/db/redis.py` (client setup)
- Keys: `app/core/keys.py` (RSA loading)
