# Runbook — Adding a New Microservice

Use this when scaffolding a new service in the monorepo.

## 1. Create the service directory

```bash
mkdir -p services/<name>-service
cd services/<name>-service
uv init --name <name>-service
```

## 2. Register in the workspace

Add to root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = [
  "services/<name>-service",
  # existing entries ...
]
```

## 3. Copy standard config files

```bash
cp services/iam-service/pyproject.toml services/<name>-service/pyproject.toml
# edit: change [project].name, remove iam-specific deps, keep ruff + pytest config
cp services/iam-service/.env.example services/<name>-service/.env.example
cp services/iam-service/justfile services/<name>-service/justfile
```

## 4. Add to docker-compose.yml

```yaml
<name>-service:
  build:
    context: ./services/<name>-service
    dockerfile: Dockerfile
  ports:
    - "<port>:8000"
  env_file:
    - ./services/<name>-service/.env
  depends_on:
    postgres:
      condition: service_healthy
```

## 5. Add CI workflow

Copy `.github/workflows/iam-service.yml` → `.github/workflows/<name>-service.yml` and update:
- `on.push.paths` — change to `services/<name>-service/**`
- `working-directory` values
- Cloud Run service name and image tag

## 6. JWT verification

If the service needs to validate IAM-issued JWTs:
1. Add `pyjwt[crypto]` and `cryptography` to its dependencies.
2. Fetch `/.well-known/jwks.json` from `iam-service` at startup and cache it.
3. Verify RS256 signatures using the public key from JWKS.
4. Do **not** connect to IAM's database — the token is the contract.

## 7. Install & run

```bash
uv sync          # from repo root
cd services/<name>-service
just runserver
```
