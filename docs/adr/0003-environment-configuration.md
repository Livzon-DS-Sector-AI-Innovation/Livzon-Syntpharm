# ADR-003: Environment Configuration

## Status
Accepted

## Context
The frontend needs to know the backend API base URL. Previously, the code had hardcoded fallbacks to `http://localhost:8000` and `http://backend:8000`, which violated our coding standards.

## Decision
Require the `API_BASE_URL` environment variable to be explicitly set. Throw a clear error if it's not set, rather than falling back to hardcoded values.

## Consequences

### Positive
- No hardcoded URLs in the codebase
- Configuration errors fail fast with clear error messages
- Explicit is better than implicit
- Complies with AGENTS.md rules

### Negative
- Requires setting API_BASE_URL in all environments
- Development setup requires one more environment variable

### Risks
- Must ensure API_BASE_URL is set in all deployment environments
- Error message must be clear enough for developers to understand the fix

## Related
- Ticket 06: Fix getApiBaseUrl() to require API_BASE_URL
- AGENTS.md: "禁止在 URL 中硬编码 localhost"
