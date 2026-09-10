# ADR-004: Frontend API Client Architecture

## Status
Accepted

## Context
The frontend needs to make API calls to the backend. We have two approaches:
1. Hand-written TypeScript types for API requests/responses
2. Generated types from the backend OpenAPI spec

## Decision
Use generated types from the OpenAPI spec exclusively. Eliminate hand-written API types.

The generated types are created by:
1. Exporting the OpenAPI spec from the backend: `uv run python scripts/ci/export_openapi.py`
2. Generating TypeScript types: `BACKEND_SPEC_PATH=../backend/openapi.json node scripts/generate-api.mjs`

## Consequences

### Positive
- Single source of truth for API contracts
- Automatic updates when backend changes
- No manual type maintenance
- Type safety guaranteed by OpenAPI spec
- Reduces duplication

### Negative
- Requires regenerating types when backend changes
- Generated types may be more verbose than hand-written types
- Build process depends on OpenAPI spec being up-to-date

### Risks
- Must ensure OpenAPI spec is always in sync with backend
- Generated types must be committed to version control
- CI must validate that generated types are up-to-date

## Related
- ADR-001: API Response Pattern
- Tickets 08-11: Generated types migration
- Ticket 12-15: Server API types migration
