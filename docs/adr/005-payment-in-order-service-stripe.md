# ADR-005 — Payment Inside order-service, Stripe-Only for v1

**Status:** Accepted
**Date:** 2026-05

## Context

Checkout needs a payment processor. We considered (a) a dedicated `payment-service`, (b) a payment bounded context inside `order-service`, and (c) deferring payment by handing off entirely to Stripe Checkout's hosted page. We also had to decide whether to support multiple processors (Stripe + PayPal + Adyen) or commit to one.

## Decision

Payment is a bounded context inside `order-service` (`app/payment/`). **Stripe is the sole processor** for v1 — no PayPal, Adyen, or in-house card vault. We use Stripe PaymentIntents (server-side confirmation flow), not Stripe Checkout, so the order-service owns the order/payment state machine. Stripe webhooks land at `POST /api/v1/payments/webhooks/stripe`, are signature-verified, and update the order via the payment use case layer.

## Consequences

- PCI scope stays at SAQ-A — card data never touches our infrastructure; Stripe Elements collects it client-side.
- Order and payment share a transaction boundary: an order's `status` and its `PaymentIntent` reference are written together.
- No provider abstraction is built up-front; a future `PaymentGateway` port can be extracted when a second processor is justified.
- Webhook delivery is at-least-once — the payment context must dedupe by Stripe event ID.
