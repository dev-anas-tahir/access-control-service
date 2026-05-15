# ADR-001 — Hexagonal Architecture for IAM Service

**Status:** Accepted  
**Date:** 2025-05

## Context

The IAM service handles authentication, RBAC, and audit logging — three distinct concerns with different change rates, external dependencies, and testing requirements. A layered-only approach would couple business logic to SQLAlchemy and FastAPI, making use cases hard to unit-test and bounded contexts hard to evolve independently.

## Decision

Adopt hexagonal (ports & adapters) architecture with three bounded contexts (`auth`, `rbac`, `audit`). Each context is strictly layered:

- **Domain** — pure Python dataclasses, `typing.Protocol` ports, exceptions. No framework imports.
- **Application** — use cases that depend only on domain ports. No SQLAlchemy, no FastAPI.
- **Infrastructure** — SQLAlchemy repos, Redis stores, FastAPI routes, JWT crypto. Implements domain ports.

Wiring happens in `<context>/infrastructure/composition.py` via FastAPI `Depends`.

## Consequences

- Use cases are unit-testable with in-memory fakes; no database required.
- Swapping infrastructure (e.g., different DB, different cache) does not touch application or domain layers.
- More files and indirection than a flat structure — acceptable cost for a security-critical service.
- `app/shared/domain/` holds entities (`User`, `Role`, `Permission`) used across all three contexts to avoid duplication.
