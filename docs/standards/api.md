# API Standards

Applies to all HTTP APIs across the monorepo.

## URL Structure

```
/api/v{n}/{resource}
```

- Plural nouns for collections: `/roles`, `/users`, `/permissions`
- No verbs in paths — use HTTP method to express the action
- Nested only one level deep: `/roles/{id}/permissions`, not `/roles/{id}/permissions/{pid}/actions`
- Admin-only paths are prefixed `/admin/` within the versioned prefix

## HTTP Methods

| Intent | Method | Success code |
|--------|--------|-------------|
| Create | POST | 201 Created |
| Read collection | GET | 200 OK |
| Read item | GET | 200 OK |
| Soft delete | DELETE | 204 No Content |
| Full replace | PUT | 200 OK |
| Partial update | PATCH | 200 OK |

## Error Shape

All errors return JSON with a `detail` field. FastAPI's default 422 shape is preserved for validation errors.

```json
{ "detail": "Role with name 'admin' already exists" }
```

For 422 validation errors FastAPI returns:
```json
{
  "detail": [
    { "loc": ["body", "name"], "msg": "field required", "type": "value_error.missing" }
  ]
}
```

## Authentication

- All protected routes require `Authorization: Bearer <access_token>`.
- Refresh token is a `refresh_token` httpOnly cookie — never put it in a header or body.
- The JWKS endpoint (`GET /.well-known/jwks.json`) is public.

## Pagination

Query params: `page` (1-based, default 1), `page_size` (default 20). Response is a plain array — no envelope wrapper.

```
GET /api/v1/admin/audit-logs?page=2&page_size=50
```

## Versioning

Current version: `v1`. A `v2` router is mounted but empty. Breaking changes require a new version prefix; non-breaking additions (new fields, new optional query params) are made in-place.
