## Problem Statement

The equipment module has accumulated significant technical debt across multiple dimensions: security vulnerabilities (missing authentication), architectural violations (cross-module imports, wrong API patterns), code hygiene issues (backup files, hardcoded paths), and type safety problems (hand-written types instead of generated). These issues were surfaced during a code review of PR #38 and represent both immediate security risks and long-term maintainability concerns.

## Solution

Systematically address all findings from the PR review in priority order:
1. **Security fixes**: Add proper authentication to all equipment API endpoints
2. **Architecture compliance**: Fix cross-module imports, API layer violations, and component organization
3. **Code hygiene**: Remove backup files, fix hardcoded paths, consolidate duplicate files
4. **Type safety**: Migrate to generated types and proper API patterns

## User Stories

1. As a security auditor, I want all equipment API endpoints to require authentication, so that unauthorized users cannot read, modify, or delete equipment data
2. As a backend developer, I want equipment module to import HR department data through public_api.py, so that module boundaries are respected and changes to HR internals don't break equipment
3. As a frontend developer, I want to use generated TypeScript types instead of hand-written ones, so that type changes in the backend automatically propagate to the frontend
4. As a frontend developer, I want write operations to go through Server Actions, so that the architecture remains consistent and testable
5. As a frontend developer, I want client components to only import client API functions, so that server-side code doesn't leak into the browser
6. As a developer, I want seed data files in the correct location (scripts/seed/), so that the repository structure follows AGENTS.md conventions
7. As a developer, I want no backup files committed to the repository, so that the codebase remains clean and professional
8. As a developer, I want no hardcoded absolute paths in scripts, so that the code works across different environments and developers
9. As a frontend developer, I want all API calls to include authentication headers, so that requests are properly authenticated
10. As a frontend developer, I want no duplicate components in multiple locations, so that I know where to find and modify components
11. As a frontend developer, I want all API calls to use the centralized API layer instead of raw fetch(), so that error handling and authentication are consistent
12. As a system administrator, I want Docker images to use multi-stage builds, so that production images are smaller and more secure
13. As a system administrator, I want Docker containers to have health checks, so that orchestration tools can detect and recover from failures
14. As a developer, I want CORS configuration to be explicit and secure, so that localhost fallbacks don't accidentally allow unauthorized origins in production
15. As a developer, I want documentation to use relative paths or environment variables, so that examples work across different setups
16. As a QA engineer, I want all equipment endpoints to have integration tests that verify authentication, so that security regressions are caught early
17. As a QA engineer, I want all API layer functions to be tested, so that type safety and error handling work correctly
18. As a developer, I want the equipment import flow to work end-to-end with proper authentication, so that users can import data securely
19. As a developer, I want the equipment batch delete flow to work through Server Actions, so that it follows the established architecture
20. As a developer, I want clear separation between client and server code in the frontend, so that the bundle size is minimized and security is maintained

## Implementation Decisions

### Security Layer
- **Authentication enforcement**: Change all `current_user: CurrentUser = None` to `current_user: CurrentUser = Depends(get_current_user)` in equipment API endpoints
- **Public endpoints**: Only `GET /template` (download template) should be public; all other endpoints require authentication
- **Audit logging**: Add audit logging for write operations (create, update, delete, import)

### Module Boundaries
- **HR department access**: Create a public API function in `app.modules.hr.public_api` that exposes department lookup functionality
- **Equipment module**: Replace direct `HrDepartment` imports with calls to the HR public API
- **Interface**: `get_department_by_name(name: str) -> Department | None` and `list_departments() -> list[Department]`

### Frontend Type Safety
- **Generated types**: Import all domain types from `@/types/generated/schema` instead of `@/types/equipment`
- **Migration path**: Update imports in all affected components, remove hand-written type definitions
- **API client**: Update client API functions to use generated types

### Frontend API Architecture
- **Server Actions**: Move all write operations (batch delete, import) to Server Actions in `app/actions/equipment.ts`
- **Client components**: Update client components to call Server Actions instead of API functions directly
- **API layer**: Ensure all API calls use the centralized client with authentication headers

### Code Hygiene
- **Backup files**: Delete `batch_import.py.bak` and `batch_import.py.backup_v3`
- **Seed data**: Move `backend/seed/departments.json` to `backend/scripts/seed/departments.json` (or consolidate if duplicate exists)
- **Hardcoded paths**: Replace `/home/zhuangweizi/...` with relative paths or `Path(__file__).parent` patterns
- **localhost fallbacks**: Remove or make explicit the localhost fallbacks in CORS and API base URL configuration

### Component Organization
- **Deduplication**: Identify the canonical location for each component (CategoryDrawer, LocationDrawer, EquipmentDrawer) and remove duplicates
- **Imports**: Update all imports to point to canonical locations

### Docker Improvements
- **Multi-stage builds**: Refactor Dockerfiles to use multi-stage builds (build stage + runtime stage)
- **Health checks**: Add HEALTHCHECK instructions using existing `/health` endpoints
- **Image size**: Target <200MB for production images

### Testing Strategy
- **Authentication tests**: Add integration tests that verify 401 responses for unauthenticated requests
- **API layer tests**: Add tests for all API client functions
- **End-to-end tests**: Add tests for import and batch delete flows with proper authentication

## Testing Decisions

### What makes a good test
- Test external behavior (HTTP responses, database state), not implementation details
- Use the highest seam possible (HTTP endpoints > service functions > repository functions)
- Mock external dependencies (database, external APIs) but test real business logic
- Include both happy path and error cases

### Modules to test
- **Authentication middleware**: Verify that protected endpoints reject unauthenticated requests
- **Equipment API endpoints**: Test all CRUD operations with authentication
- **Import flow**: Test preview → confirm → complete flow with authentication
- **Batch delete flow**: Test deletion with authentication and authorization
- **API client functions**: Test that authentication headers are included
- **Server Actions**: Test that they properly authenticate and call backend APIs

### Prior art
- Look at existing tests in `backend/tests/modules/` for patterns
- Follow the Server Actions testing pattern from other modules
- Use the existing MockDB pattern for database mocking

## Out of Scope

- **Database migrations**: No schema changes required for this cleanup
- **New features**: No new functionality, only fixing existing issues
- **Performance optimization**: Not addressing performance unless directly related to findings
- **Documentation overhaul**: Only fixing hardcoded paths in documentation, not rewriting docs
- **CI/CD pipeline changes**: Not modifying the CI configuration itself
- **Other modules**: Only fixing equipment module; other modules may have similar issues but are out of scope

## Further Notes

### Priority Order
1. **Security fixes** (blocking): Authentication, CORS, auth headers
2. **Architecture compliance** (high): Module boundaries, Server Actions, component organization
3. **Type safety** (medium): Generated types, API layer
4. **Code hygiene** (low): Backup files, hardcoded paths, duplicates
5. **Docker improvements** (low): Multi-stage builds, health checks

### Risk Assessment
- **Authentication changes**: May break existing integrations; need to coordinate with frontend team
- **Type migration**: Large surface area; need to test thoroughly
- **Server Actions migration**: May require frontend refactoring; need to update multiple components

### Dependencies
- HR module must expose public API for department lookup before equipment module can be updated
- Generated types must be up-to-date before frontend migration
- Authentication middleware must be working before endpoint protection

### Rollback Plan
- Each category of fixes can be deployed independently
- Security fixes should be deployed first and can be rolled back independently
- Architecture changes should be deployed together to maintain consistency

### Success Criteria
- All 17 blocking findings resolved
- All 15 high-priority findings resolved
- CI passes with strict type checking
- No security vulnerabilities in security scan
- Code review approval from architecture team

