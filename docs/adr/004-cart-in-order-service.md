# ADR-004 — Cart Lives in order-service (Deferred to Post-MVP)

**Status:** Accepted
**Date:** 2026-05

## Context

An ecommerce platform needs a shopping cart. We considered three placements: a standalone `cart-service`, a context inside `order-service`, or a client-only cart held in the BFF / `localStorage`. We also needed to decide whether the MVP ships with a cart at all or only a direct buy-now checkout.

## Decision

The cart is a bounded context inside `order-service` (`app/cart/`) and is **deferred** until after the first paid checkout ships. The MVP exposes only `POST /orders` with an explicit `line_items[]` payload — the client (or BFF) assembles them. When the cart context lands, it will share `order-service`'s database so cart-to-order conversion is a single transaction.

## Consequences

- No new deployable: cart, order, and payment live behind one service boundary and one schema.
- Cart-abandonment notifications, persisted multi-device carts, and merge-on-login are out of scope until the cart context exists.
- Co-locating cart with order requires us to honour the same hexagonal layering — cart use cases must not import from `order/`.
- If cart traffic ever dwarfs order traffic, it can be extracted; the bounded-context boundary inside `order-service` keeps that path open.
