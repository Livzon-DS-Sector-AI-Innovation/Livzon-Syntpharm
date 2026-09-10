# Equipment Module Audit Fixes - Phase 2

## Problem Statement

The equipment module has accumulated technical debt across multiple areas:

1. **Documentation contains hardcoded absolute paths** that violate project conventions and make documentation non-portable across environments
2. **Test infrastructure has multiple anti-patterns** including module-level side effects, unsafe cleanup, type suppressions, and missing parametrization opportunities
3. **Frontend architecture violations** where page-level components are placed in the wrong directory structure
4. **Type safety issues** in frontend components using `any` types instead of generated schema types
5. **API client layer uses untyped parameters** (`data: any`) throughout, bypassing TypeScript's type safety and OpenAPI contract validation
6. **Raw fetch calls** in server API layer bypass the authenticated API client abstraction

These issues reduce code maintainability, type safety, and violate established project conventions documented in AGENTS.md.

## Solution

Systematically address all audit findings in priority order:

1. Replace hardcoded paths in documentation with relative paths or environment variables
2. Refactor test infrastructure to follow pytest best practices: fixture-based setup, safe cleanup with try/finally, proper type annotations, and parametrization
3. Move page-level components to correct Next.js app router directory structure
4. Replace `any` types with generated schema types from OpenAPI spec
5. Replace all `data: any` parameters with typed interfaces from generated schema
6. Replace raw fetch calls with authenticated API client methods

## User Stories

1. As a developer, I want documentation to use relative paths so that examples work across different environments without modification
2. As a developer, I want tests to use fixture-based setup so that test state is properly isolated and cleaned up
3. As a developer, I want tests to use proper type annotations so that type errors are caught at compile time
4. As a developer, I want similar test cases to use parametrize so that test code is DRY and easy to maintain
5. As a developer, I want integration tests in the correct directory so that test organization follows project conventions
6. As a developer, I want page components in the app router directory so that Next.js routing conventions are followed
7. As a developer, I want frontend components to use typed props so that type errors are caught at compile time
8. As a developer, I want API client functions to use typed parameters so that API contracts are enforced by TypeScript
9. As a developer, I want all API calls to use the authenticated client so that auth headers are consistently applied
10. As a developer, I want the OpenAPI spec to be the single source of truth for API types so that frontend and backend stay in sync

## Implementation Decisions

### Documentation Fixes
- Replace all hardcoded absolute paths with relative paths or placeholder variables
- Use `$(pwd)` or relative path notation in shell command examples
- Update both flexible-import-guide.md and department-seeding-summary.md

### Test Infrastructure Refactoring
- Move TestClient initialization into fixtures using pytest fixtures
- Replace manual `dependency_overrides.clear()` with try/finally blocks or fixture-based cleanup
- Remove all `# type: ignore[arg-type]` suppressions by defining proper Protocol types for mock objects
- Consolidate similar test cases using `@pytest.mark.parametrize`
- Move integration test (test_import_api_integration.py) to backend/tests/integration/
- Remove duplicate imports in test_department_mapping.py by moving imports to module level

### Frontend Architecture Fixes
- Move EquipmentPage component from src/components/equipment/ to src/app/(dashboard)/equipment/
- Update imports in all files that reference the moved component
- Ensure the component follows Next.js app router conventions

### Frontend Type Safety
- Replace `initialData?: any` in CategoryEditor and LocationEditor with proper generated types
- Use `components['schemas']['EquipmentCategoryUpdate']` and `components['schemas']['LocationUpdate']` from generated schema
- Ensure all component props are properly typed

### API Client Type Safety
- Replace all `data: any` parameters in src/lib/api/server/equipment.ts with typed interfaces
- Use generated types from components['schemas'] for all request bodies
- Create type aliases for complex request types if needed
- Ensure all API functions have proper return types

### Raw Fetch Replacement
- Replace all raw `fetch()` calls with `apiFetch()` or `apiFetchRaw()` from the authenticated client
- Ensure all API calls go through the authenticated client layer
- Verify that auth headers are properly applied in all cases

## Testing Decisions

### What Makes a Good Test
- Tests should verify external behavior, not implementation details
- Tests should be isolated and not depend on execution order
- Tests should use fixtures for setup and cleanup
- Tests should have proper type annotations
- Similar test cases should be parametrized to reduce duplication

### Modules to Test
- Documentation examples (manual verification)
- Test infrastructure (run existing test suite to verify no regressions)
- Frontend components (TypeScript compilation check)
- API client layer (TypeScript compilation check)
- Integration tests (run existing integration test suite)

### Prior Art
- Existing test fixtures in backend/tests/conftest.py
- Existing typed API clients in other modules (e.g., quality, registration)
- Existing page components in src/app/(dashboard)/ structure
- Existing generated types in src/types/generated/schema.ts

## Out of Scope

- Adding new features or functionality to the equipment module
- Refactoring business logic or service layer code
- Changing API endpoints or contracts
- Modifying database schema or models
- Updating other modules beyond the equipment module
- Performance optimizations or caching improvements

## Further Notes

### Priority Order
1. **Blocking**: API client type safety (data: any) - prevents type errors from reaching production
2. **High**: Frontend architecture violations - violates Next.js conventions
3. **Medium**: Test infrastructure issues - reduces test maintainability
4. **Medium**: Frontend type safety (initialData?: any) - reduces type safety
5. **Low**: Documentation hardcoded paths - non-portable documentation
6. **Low**: Test pattern improvements - code quality improvements

### Dependencies
- API client type safety depends on having up-to-date OpenAPI spec
- Frontend type safety depends on generated types being available
- Test refactoring should be done incrementally to avoid breaking existing tests

### Risk Mitigation
- Each change should be committed separately for easy rollback
- Run full test suite after each major change
- Verify TypeScript compilation passes after type-related changes
- Verify documentation examples are still valid after path updates

### Success Criteria
- All hardcoded paths removed from documentation
- All tests use fixture-based setup and cleanup
- No `# type: ignore` suppressions in equipment tests
- Similar test cases are parametrized
- Integration tests are in correct directory
- Page components are in correct directory structure
- No `any` types in component props
- No `data: any` in API client functions
- No raw fetch calls in API client layer
- TypeScript compilation passes with strict mode
- All existing tests continue to pass
