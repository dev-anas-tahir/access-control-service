# ADR-008 — Postgres Full-Text Search over Elasticsearch

**Status:** Accepted
**Date:** 2026-05

## Context

Catalog needs search across product name, description, SKU, and category. Options were (a) Elasticsearch / OpenSearch as a sidecar with a CDC pipeline from Postgres, (b) a managed search SaaS (Algolia, Typesense Cloud), or (c) Postgres' built-in `tsvector` / `tsquery` with a GIN index. Catalog volume at launch is in the low thousands of variants; merchants haven't asked for faceted navigation.

## Decision

Catalog search uses **Postgres FTS**. `products` and `product_variants` carry a generated `search_vector tsvector` column weighted (`A` = name/SKU, `B` = category, `C` = description) and indexed with GIN. Queries go through `to_tsquery('english', …)` with `plainto_tsquery` for user input. The search endpoint lives in `catalog-service` and reuses the existing repository layer.

## Consequences

- Zero new infrastructure: no Elasticsearch cluster, no CDC pipeline, no eventual-consistency window between writes and search results.
- Faceting, fuzzy matching, and language-aware stemming beyond Postgres' built-ins are not available — accepted for v1.
- The search vector is a generated column, so re-indexing on schema change requires a migration but no application-level backfill job.
- Reassessment trigger documented: extract to Elasticsearch when catalog passes ~1M variants or merchants demand faceted navigation. That decision will get its own ADR.
