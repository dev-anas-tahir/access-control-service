# Catalog Service — Domain Context

## Bounded Contexts

| Context | Aggregates | Responsibility |
|---------|-----------|----------------|
| `catalog/` | `Product`, `ProductVariant`, `Category` | Product metadata, taxonomy, lifecycle |
| `inventory/` | `Inventory` | Stock levels, reservations |

---

## Glossary

### Product
A sellable item with metadata. Has a lifecycle status of `active` or `inactive`. Inactive products are hidden from the storefront. Belongs to exactly one `Category`. A `Product` is never directly purchasable — its `ProductVariant's` are.

### ProductVariant
A specific, purchasable form of a `Product` (e.g. a T-shirt in size M / color red). Carries its own `sku`, `price`, and free-form `attributes` (JSONB). The variant is the unit that appears in a cart or order line item.

### Category
A node in a single-parent taxonomy tree (`parent_id | None`). Depth is unbounded; recursive CTEs handle descendant queries. Each `Product` has exactly one primary `Category`.

### Inventory
Tracks stock for a single `ProductVariant`. Maintains `quantity_on_hand` and `quantity_reserved`. Available stock = `on_hand − reserved`. Reservations are created during checkout and committed (decremented from `on_hand`) or released on cancellation.

`Inventory` is a **tell-don't-ask aggregate**: all state transitions go through its methods, which enforce invariants and buffer domain events internally. The Unit of Work drains the buffer via `collect_events()` after `commit()`.

### Reservation
A soft hold on `Inventory` placed during checkout. Prevents oversell under concurrent writes. Not a standalone aggregate — lives as a quantity on the `Inventory` record.

**Release and commit are forgiving**: `release(qty)` and `commit_reservation(qty)` silently clamp to `min(qty, quantity_reserved)`. Callers (e.g. order-service retrying a partial commit) need not know the exact reserved quantity. Reserving more than `available`, by contrast, is strict — raises `InsufficientStockError`.

### ProductPublished event
Fired when a `Product` transitions from `inactive → active`. Consumed downstream by order-service and notification-service via Pub/Sub.

### ProductPriceChanged event
Fired when a `ProductVariant.price` is updated while its parent `Product` is `active`. Downstream services may need to re-price in-flight carts.

### InventoryRestocked / InventoryDepleted events
Fired when `Inventory.quantity_on_hand` crosses zero. `InventoryRestocked` fires inside `restock()` when on-hand rises above zero from zero. `InventoryDepleted` fires inside `commit_reservation()` when on-hand reaches zero — **not** during `reserve()` (reserving moves stock from available to reserved but does not change on-hand). Notification-service subscribes.

---

## Authorization

- **Reads** — public, no token required.
- **Mutations** — require a valid RS256 JWT (issued by iam-service) with the `catalog:write` permission claim.
- JWT verification uses JWKS fetch from iam-service at startup; public key is cached in-process.

---

## Key Invariants

- A `ProductVariant` SKU is globally unique.
- `Inventory.quantity_reserved` never exceeds `quantity_on_hand`.
- `ProductPublished` is emitted only on `inactive → active` transition, not on re-saves of already-active products.
- Hard deletes are forbidden; use `Product.status = inactive` and `Inventory` quantity zeroing instead.
