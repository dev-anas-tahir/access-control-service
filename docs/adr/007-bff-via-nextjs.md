# ADR-007 — Web BFF via Next.js (No Standalone Node BFF)

**Status:** Accepted
**Date:** 2026-05

## Context

The web client needs to aggregate calls across `iam-service`, `catalog-service`, and `order-service`, and must keep access tokens out of browser JavaScript to limit XSS blast-radius. Options were: (a) a standalone Node BFF (e.g. NestJS) sitting in front of the services, (b) Next.js Route Handlers / Server Actions acting as the BFF, or (c) calling backend services directly from the browser with tokens in `localStorage`.

## Decision

`apps/web` (Next.js) **is** the BFF. Server-side Route Handlers and Server Actions proxy backend calls. The refresh token lives in an `HttpOnly; Secure; SameSite=Lax` cookie set by Next.js; the short-lived access token is fetched server-side per request and never sent to client JS. The mobile app talks directly to backend services and holds tokens in its secure keychain.

## Consequences

- One fewer deployable: no separate Node BFF to operate, log, or scale.
- Server Components can call services directly with the user's token — no double-hop for SSR pages.
- Web and mobile have **different** security models: cookie-bound for web, bearer-bound for mobile. CSRF protection (double-submit token) is required on web mutation routes; mobile is exempt.
- Coupling the BFF to Next.js means a frontend rewrite would also require rebuilding the BFF — acceptable given a single web client.
