# ADR-002: Exception Hierarchy

## Status
Accepted

## Context
We need a consistent exception hierarchy for error handling across the backend. FastAPI provides HTTPException, but we need domain-specific exceptions with consistent error messages.

## Decision
Create a custom exception hierarchy inheriting from AppException:
- `BadRequestException`: For 400 Bad Request errors
- `NotFoundException`: For 404 Not Found errors
- `DuplicateException`: For 409 Conflict errors
- `ForbiddenException`: For 403 Forbidden errors
- `UnauthorizedException`: For 401 Unauthorized errors

All exceptions inherit from `AppException` which inherits from `HTTPException`.

## Consequences

### Positive
- Consistent error messages across the application
- Domain-specific exceptions are more expressive
- Easier to handle specific error types
- Centralized error message management

### Negative
- Need to maintain custom exception classes
- Developers need to learn which exception to use

### Risks
- Must ensure all endpoints use the custom exceptions
- Error messages should be reviewed for consistency

## Related
- ADR-001: API Response Pattern
- Ticket 01: Add BadRequestException class
