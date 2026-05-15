# Runbook — RSA Key Rotation

Rotate the RSA key pair used to sign and verify JWTs. Required when: a key is compromised, reaching rotation schedule, or deploying a new environment.

## Impact

- All existing access tokens (up to 15 min old) continue to be valid during the transition window.
- Refresh tokens are unaffected — they are opaque secrets stored in Redis, not signed with RSA.
- Downstream services caching the JWKS response will verify tokens with the old key until their cache expires.

## Prerequisites

- SSH or Cloud Run console access to the `iam-service` deployment
- GCP Secret Manager write access (production) or filesystem access (dev/staging)

---

## Steps

### 1. Generate new key pair

```bash
openssl genrsa -out keys/new_private_key.pem 2048
openssl rsa -in keys/new_private_key.pem -pubout -out keys/new_public_key.pem
```

### 2. Upload to Secret Manager (production)

```bash
gcloud secrets versions add iam-private-key --data-file=keys/new_private_key.pem
gcloud secrets versions add iam-public-key  --data-file=keys/new_public_key.pem
```

### 3. Update JWKS endpoint

The current implementation serves a single key. Before switching, verify that downstream services (catalog-service, order-service) do **not** pin a specific `kid`. If they cache JWKS, ensure their cache TTL is ≤ 15 minutes.

### 4. Deploy with new key paths

Update `PRIVATE_KEY_PATH` and `PUBLIC_KEY_PATH` environment variables in the Cloud Run service, then redeploy:

```bash
gcloud run services update iam-service \
  --update-env-vars PRIVATE_KEY_PATH=/secrets/new_private_key.pem,PUBLIC_KEY_PATH=/secrets/new_public_key.pem \
  --region <REGION>
```

### 5. Monitor for 401 errors

Watch logs for a spike in `401 InvalidTokenError` — this indicates tokens signed with the old key are being rejected. The window is at most 15 minutes (access token TTL).

```bash
gcloud logging read 'resource.type="cloud_run_revision" severity>=ERROR jsonPayload.message=~"InvalidToken"' \
  --freshness=30m --format=json
```

### 6. Revoke old key version

Once 15 minutes have elapsed with no old-key errors:

```bash
gcloud secrets versions disable <OLD_VERSION> --secret=iam-private-key
gcloud secrets versions disable <OLD_VERSION> --secret=iam-public-key
```

---

## Rollback

If the new key causes widespread failures, redeploy with the previous key paths. Old access tokens (≤15 min) will resume working immediately.
