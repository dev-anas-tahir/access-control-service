# ADR-006 — JWKS-Based Auth Across Downstream Services

**Status:** Accepted
**Date:** 2026-05

## Context

[[ADR-002]] established that `iam-service` issues RS256 JWTs and exposes a JWKS endpoint. That decision left open *how* downstream services consume tokens: per-request introspection against IAM, a shared signing secret, or local verification via JWKS. We needed one rule so catalog, order, and any future service authenticate identically.

## Decision

Every non-IAM service verifies JWTs **locally** using the public key fetched once from `GET /.well-known/jwks.json` at app startup and cached in-process (`JwksClient` singleton). Authorization claims (`roles[]`, `permissions[]`, `is_super_user`) embedded in the token are trusted without an IAM round-trip. Each service exposes scoped FastAPI dependencies — e.g. `require_catalog_write` — that decode the token and check the relevant claim. Startup fails fast if JWKS is unreachable.

## Consequences

- Request path never touches `iam-service` — latency stays low and IAM outage doesn't take catalog/order down for already-issued tokens.
- Revocation is bounded by the 15-minute access-token TTL; instant global revocation is not supported by design.
- Permission changes in IAM only take effect when the user's next token is issued — acceptable for an RBAC model, not for fine-grained ACLs.
- Key rotation requires a brief overlap window; runbook lives at [`../runbooks/key-rotation.md`](../runbooks/key-rotation.md).
