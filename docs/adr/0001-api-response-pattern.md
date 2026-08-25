# ADR-001: API Response Pattern

## Status
Accepted

## Context
We need a consistent pattern for API responses across the backend. There are two response helper functions available:
- `success_response()`: Returns a JSONResponse directly
- `build_response()`: Returns an ApiResponse model that FastAPI can validate

## Decision
Use `build_response()` for all new endpoints instead of `success_response()`.

## Consequences

### Positive
- FastAPI can validate response data against the response_model
- OpenAPI schema generation is more accurate
- Better type safety and documentation
- Consistent with FastAPI best practices

### Negative
- Requires explicit response_model on endpoints
- Slightly more verbose than success_response()

### Risks
- Existing endpoints using success_response() need to be migrated gradually
- Must ensure response_model matches the actual response structure

## Related
- ADR-002: Exception Hierarchy
- Ticket 03: Migrate batch_import.py to build_response
