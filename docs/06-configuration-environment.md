# Configuration & Environment

## Configuration File (`app/config.py`)

### Settings Class Structure

```python
class Settings(BaseSettings):
    # Application settings
    app_env: str = "development"
    app_name: str = "access-control-service"
    app_debug: bool = False
    log_level: str = "INFO"

    # Database
    database_url: PostgresDsn  # Required
    test_database_url: PostgresDsn | None = None
    pool_size: int = 10
    max_overflow: int = 20

    # Cache
    redis_url: RedisDsn  # Required

    # JWT
    jwt_algorithm: str = "RS256"
    jwt_issuer: str = "access-control-service"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7
    private_key_path: Path = Path("keys/private_key.pem")
    public_key_path: Path = Path("keys/public.pem")

    # GCP
    gcp_project_id: str  # Required
    pubsub_topic_id: str  # Required

    class Config:
        env_file = BASE_DIR / ".env"
        case_sensitive = False

settings = Settings()
```

**File**: `app/config.py:28-86`

---

## Environment Variables Reference

### Application

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `app_env` | string | `"development"` | Environment name: `development`, `staging`, `production` |
| `app_name` | string | `"access-control-service"` | Application identifier |
| `app_debug` | boolean | `False` | Enable debug mode (SQL query logging) |
| `log_level` | string | `"INFO"` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

### Database

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `database_url` | PostgresDsn | **Required** | Async PostgreSQL DSN: `postgresql+asyncpg://user:pass@host:port/dbname` |
| `test_database_url` | PostgresDsn | `None` | Test database URL (overrides production in tests) |
| `pool_size` | integer | `10` | Connection pool size |
| `max_overflow` | integer | `20` | Maximum additional connections during spikes |

**Connection Pool Total**: `pool_size + max_overflow` (30 by default)

---

### Cache (Redis)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `redis_url` | RedisDsn | **Required** | Redis connection URL: `redis://host:port` or `rediss://` for TLS |

**With Authentication** (if needed):
```
redis://:password@host:port
```

---

### JWT

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `jwt_algorithm` | string | `"RS256"` | Signing algorithm (RS256 only currently) |
| `jwt_issuer` | string | `"access-control-service"` | Issuer claim value |
| `jwt_access_token_expire_minutes` | integer | `15` | Access token lifetime |
| `jwt_refresh_token_expire_days` | integer | `7` | Refresh token lifetime |
| `private_key_path` | Path | `"keys/private_key.pem"` | RSA private key file path |
| `public_key_path` | Path | `"keys/public.pem"` | RSA public key file path |

**Key Format**: PEM-encoded RSA keys (PKCS#1 or PKCS#8)

---

### GCP (Google Cloud Platform)

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `gcp_project_id` | string | **Required** | GCP project ID (e.g., `"my-project-123"`) |
| `pubsub_topic_id` | string | **Required** | Pub/Sub topic name for activity logging |

**Example**:
```
gcp_project_id=access-control-prod
pubsub_topic_id=activity-log
```

---

## Configuration Examples

### Development (`.env`)

```ini
# .env (development)
app_env=development
app_debug=true
log_level=DEBUG

# Local PostgreSQL (Docker)
database_url=postgresql+asyncpg://postgres:postgres@localhost:5432/access_control_dev

# Local Redis (Docker)
redis_url=redis://localhost:6379/0

# JWT - Local keys (generate with openssl)
private_key_path=keys/private_key.pem
public_key_path=keys/public.pem

# GCP - Not required for local dev (but must be set)
gcp_project_id=dummy-project
pubsub_topic_id=dummy-topic
```

### Staging/Production (`.env` or GCP Secret Manager)

```ini
# .env (never committed) or injected via environment
app_env=production
app_debug=false
log_level=INFO

# Cloud SQL with pgBouncer or direct connection
database_url=postgresql+asyncpg://user:password@/dbname?host=/cloudsql/project:region:instance

# Memorystore Redis
redis_url=rediss://10.0.0.1:6379/0  # TLS recommended

# JWT keys from Secret Manager mounted to /var/secrets or injected as env vars
# (see below for alternative approach)
private_key_path=/var/secrets/jwt-private.pem
public_key_path=/var/secrets/jwt-public.pem

# GCP
gcp_project_id=my-production-project
pubsub_topic_id=access-control-activity
```

---

## Secret Management Strategies

### Option 1: File-based (Current Implementation)

- **Development**: Keys stored in `keys/` directory (gitignored)
- **Production**: Override `RSAKeyPair.load()` to read from secure location
- **Drawback**: Requires filesystem access; not ideal for serverless (Cloud Run)

### Option 2: GCP Secret Manager

Mount secrets as files or fetch via API:

```python
from google.cloud import secretmanager

def load_keys_from_secret_manager():
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{settings.gcp_project_id}/secrets/jwt-private/versions/latest"
    response = client.access_secret_version(name=name)
    private_key_pem = response.payload.data.decode("UTF-8")
    # Similarly for public key
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode(), password=None
    )
    RSAKeyPair.private_key = private_key
    # ... load public key
```

**IAM Role**: `roles/secretmanager.secretAccessor`

**Recommended for Production**.

---

### Option 3: Environment Variables (PEM strings)

For serverless deployments (Cloud Run), inject PEM contents as env vars:

```ini
JWT_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."
JWT_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n..."
```

Modify `config.py`:
```python
jwt_private_key_data: str | None = None
jwt_public_key_data: str | None = None
```

And `keys.py`:
```python
if settings.jwt_private_key_data:
    private_key = serialization.load_pem_private_key(
        settings.jwt_private_key_data.encode(), password=None
    )
```

---

## Configuration Validation

Pydantic automatically validates types and constraints on startup. Invalid configuration raises `ValidationError` during `Settings()` instantiation.

**Example error**:
```bash
pydantic_core._pydantic_core.ValidationError: 2 validation errors for Settings
database_url
  Field required [type=missing, input_value={...}]
gcp_project_id
  Field required [type=missing, input_value={...}]
```

---

## Overriding Settings in Tests

Test overrides in `tests/conftest.py`:

```python
@pytest.fixture(scope="session", autouse=True)
def override_settings():
    # Use test database
    original = settings.database_url
    settings.database_url = settings.test_database_url or original
    yield
    settings.database_url = original
```

**`tests/integration/conftest.py`**:
```python
@pytest.fixture(scope="session", autouse=True)
def override_engine(engine):
    import app.shared.infrastructure.db.session as session_module
    session_module.async_engine = engine
```

---

## Named Configuration Profiles

While `app_env` is available, there's no formal profile system. To add:

```python
class Settings(BaseSettings):
    @classmethod
    def from_profile(cls, profile: str):
        if profile == "production":
            return cls(
                app_env="production",
                app_debug=False,
                database_url=...,
                # ...
            )
        return cls()  # default (development)
```

Alternatively, use `.env.{profile}` files and load based on `APP_ENV`:

```python
env_file = BASE_DIR / f".env.{os.getenv('APP_ENV', 'development')}"
if env_file.exists():
    settings = Settings(_env_file=env_file)
```

---

## References

- Configuration class: `app/config.py:28-86`
- Settings usage: `app/main.py`, `app/shared/infrastructure/db/session.py`, `app/auth/infrastructure/crypto/key_pair.py`, etc.
- Environment loading: Pydantic `BaseSettings` documentation
