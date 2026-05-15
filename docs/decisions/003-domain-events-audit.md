# ADR-003 — Domain Events for RBAC → Audit Decoupling

**Status:** Accepted  
**Date:** 2025-05

## Context

Every RBAC mutation (create role, assign permission, assign role to user, etc.) must produce an audit log entry. The naive approach — having RBAC use cases directly call the audit logger — couples the two bounded contexts at the import level and makes the audit write an afterthought.

## Decision

RBAC use cases emit typed domain events (`RoleCreated`, `PermissionGranted`, `UserRoleAssigned`, …) via `uow.add_event(event)`. After `uow.commit()` persists the business change, the Unit of Work calls `collect_events()` and dispatches each event to `SqlAlchemyAuditLogger.log()`. The audit insert runs in a separate commit within the same session.

```
Use case
  └─ uow.add_event(RoleCreated(...))
  └─ uow.commit()          ← business INSERT committed
     └─ collect_events()
        └─ AuditLogger.log(event)   ← audit INSERT committed
```

The `rbac/` context never imports from `audit/`. The logger is injected into `SqlAlchemyRbacUnitOfWork` via `composition.py`.

## Consequences

- `rbac/` and `audit/` have no compile-time dependency on each other.
- Adding a new event subscriber (e.g., Pub/Sub publisher) requires only a new handler in `composition.py`.
- Audit writes are synchronous and in the same DB session — no eventual consistency. If the audit insert fails the exception surfaces to the caller after the business commit has already succeeded; this is an acceptable trade-off for now.
- All RBAC events implement `to_audit_payload() -> dict` for consistent serialisation.
