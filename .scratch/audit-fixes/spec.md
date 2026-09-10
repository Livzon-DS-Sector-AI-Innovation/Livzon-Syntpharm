# Equipment Module Audit Fixes

## Problem Statement

The equipment module has accumulated technical debt identified through a comprehensive audit. The audit found 25+ issues across four severity levels:

- **4 blocking issues**: Hand-written API types that bypass generated types from OpenAPI spec
- **6 high priority issues**: Hardcoded localhost URLs, direct fetch calls without auth headers, page components in wrong locations
- **10 medium priority issues**: Incorrect exception handling, inconsistent response patterns, duplicated test fixtures, missing type annotations
- **5 low priority issues**: Documentation with hardcoded paths, test organization issues, redundant pytest markers

These issues create maintenance burden, reduce type safety, and violate project conventions documented in AGENTS.md.

## Solution

Fix all issues in a single PR following a dependency-based implementation order. Create Architecture Decision Records (ADRs) for key architectural decisions and update the domain glossary (CONTEXT.md) to document important terms.

The fixes will:
1. Eliminate hand-written API types in favor of generated types from OpenAPI spec
2. Standardize exception handling using a new BadRequestException class
3. Migrate to the correct response pattern (build_response instead of success_response)
4. Extract shared test fixtures to reduce duplication
5. Remove hardcoded localhost URLs per AGENTS.md rules
6. Replace raw fetch calls with authenticated API helpers
7. Add proper type annotations to replace `data: any` patterns
8. Document key architectural decisions in ADRs

## User Stories

1. As a developer, I want all API client types to be generated from OpenAPI spec, so that I have a single source of truth and automatic updates when the backend changes
2. As a developer, I want consistent exception handling across the equipment module, so that error responses are predictable and follow the established pattern
3. As a developer, I want all endpoints to use build_response() instead of success_response(), so that FastAPI can validate responses and generate accurate OpenAPI schemas
4. As a developer, I want shared test fixtures in conftest.py, so that I don't duplicate MockDB and helper functions across test files
5. As a developer, I want environment variables to be required rather than falling back to hardcoded values, so that configuration errors fail fast instead of silently using wrong URLs
6. As a developer, I want all API calls to use authenticated helpers (apiGet/apiFetch), so that auth headers are automatically included and I don't make raw fetch calls
7. As a developer, I want proper type annotations for request bodies, so that Pydantic can validate inputs and catch errors early
8. As a developer, I want architectural decisions documented in ADRs, so that future developers understand why we made certain choices
9. As a developer, I want the domain glossary to include important terms, so that we use consistent language across the codebase
10. As a developer, I want test imports to be clean and redundant markers removed, so that tests are easier to read and maintain
11. As a developer, I want CRUD operations to have proper types instead of `data: any`, so that I get type safety and autocomplete
12. As a developer, I want the OpenAPI spec to be regenerated when backend changes, so that frontend types stay in sync

## Implementation Decisions

### Exception Hierarchy
- Add `BadRequestException` class to `app/core/exceptions.py` to match the existing pattern (NotFoundException, DuplicateException, etc.)
- Replace all `HTTPException(status_code=400, detail=...)` with `BadRequestException(message=...)` in batch_import.py

### Response Pattern Migration
- Migrate batch_import.py endpoints from `success_response()` to `build_response()`
- Ensure response_model is set correctly on each endpoint
- Do this incrementally, testing each endpoint after migration

### Test Fixture Organization
- Create `backend/tests/modules/equipment/conftest.py` for equipment-specific shared fixtures
- Move `MockDB`, `_extract_param_values`, and `create_mock_department` to conftest.py
- Update all equipment test files to import from conftest

### Type Safety for Import
- Create `EquipmentImportRow` Pydantic model in `app/modules/equipment/schemas/equipment.py`
- Define fields: 资产编号, 资产说明, 实物所在部门, 资产类别说明, 当前成本, 报废状态, 数量, etc.
- Use this model in preview_import and batch_import endpoints instead of `list[dict[str, Any]]`

### Generated Types Migration
- Replace hand-written `EquipmentStatisticsFilters` and `FetchEquipmentsClientParams` with generated types from schema.ts
- Extract query parameter types from operations: `operations["get_equipments_api_v1_equipment_equipments_get"]["parameters"]["query"]`
- Update all client API files (src/lib/api/client/*.ts) to use generated types

### Server API Type Annotations
- Replace `data: any` with proper types in all CRUD operations
- Use generated types from schema.ts for request bodies
- Do this incrementally, starting with critical functions

### Environment Configuration
- Modify `getApiBaseUrl()` in `src/lib/api/server/base.ts` to throw an error if `API_BASE_URL` is not set
- Remove hardcoded fallbacks to `http://localhost:8000` and `http://backend:8000`
- This enforces AGENTS.md rule: "禁止在 URL 中硬编码 localhost"

### API Client Consistency
- Replace raw `fetch()` calls with `apiGet()`/`apiFetch()` helpers
- Update `fetchInspectionTemplateItemsClient` and `batchDeleteEquipments` to use authenticated helpers
- This ensures auth headers are automatically included

### Test Improvements
- Remove redundant `@pytest.mark.asyncio` markers (pyproject.toml sets asyncio_mode = "auto")
- Consolidate duplicate imports in test files
- Extract shared fixtures to conftest.py

### Page Component Location
- Keep `EquipmentPage.tsx` in `src/components/equipment/` (current location)
- The current pattern works and moving it would require updating imports
- This is a low-value refactor that doesn't improve functionality

### Architecture Decision Records
- Create ADR-001: API Response Pattern (why we use build_response instead of success_response)
- Create ADR-004: Frontend API Client Architecture (why we use generated types instead of hand-written types)
- These decisions are hard to reverse, surprising without context, and result from real trade-offs

### Domain Glossary Updates
- Add "API Response Envelope" to CONTEXT.md: The standard response structure {code, data, message, meta}
- Add "Generated Types" to CONTEXT.md: TypeScript types automatically generated from backend OpenAPI spec

### Implementation Order
1. Add BadRequestException class
2. Create EquipmentImportRow Pydantic model
3. Migrate batch_import.py to use build_response() and BadRequestException
4. Replace hand-written types with generated types in client API files
5. Replace data: any with proper types in CRUD operations
6. Extract test fixtures to conftest.py
7. Fix hardcoded localhost in getApiBaseUrl()
8. Replace raw fetch with apiGet/apiFetch
9. Update test imports and remove redundant markers
10. Create ADRs and update CONTEXT.md

## Testing Decisions

### What Makes a Good Test
- Test external behavior, not implementation details
- Use the highest seam possible (prefer integration tests over unit tests when appropriate)
- Minimize the number of seams across the codebase

### Modules to Test
- `batch_import.py`: Test preview_import and batch_import endpoints with proper Pydantic validation
- Exception handling: Verify BadRequestException returns correct status codes and messages
- Response pattern: Verify build_response() returns ApiResponse model that FastAPI can validate
- Test fixtures: Verify shared fixtures work correctly across all equipment test files
- Type safety: Verify generated types match backend OpenAPI spec
- Environment configuration: Verify getApiBaseUrl() throws error when API_BASE_URL is not set

### Prior Art
- Existing equipment tests in `backend/tests/modules/equipment/`
- Existing test fixtures in `backend/tests/conftest.py` (if any)
- Existing ADRs in `docs/adr/` (if any)

## Out of Scope

- Moving `EquipmentPage.tsx` to a different location (current location works fine)
- Regenerating OpenAPI spec for every backend change (this is already handled by CI)
- Creating ADRs for standard patterns (only non-obvious decisions get ADRs)
- Adding all possible terms to CONTEXT.md (only important domain concepts)
- Fixing issues in other modules (this spec focuses on equipment module only)
- Refactoring the entire API client layer (only fixing the issues identified in the audit)

## Further Notes

### OpenAPI Spec Regeneration
The OpenAPI spec was regenerated during this work using:
```bash
cd backend && uv run --python 3.12 python scripts/ci/export_openapi.py
cd frontend && BACKEND_SPEC_PATH=../backend/openapi.json node scripts/generate-api.mjs
```

This ensures frontend types are in sync with the backend.

### Dependency Order Rationale
The implementation order is based on dependencies:
- BadRequestException must exist before we can use it in batch_import.py
- EquipmentImportRow must exist before we can use it in batch_import.py
- build_response() migration should happen before type annotation fixes
- Test fixtures should be extracted before updating test imports
- ADRs and CONTEXT.md updates should happen last (documentation)

### Risk Mitigation
- Each step is independently testable
- We're following existing patterns (BadRequestException matches other exception classes)
- We're using generated types (single source of truth)
- We're documenting decisions (ADRs) for future reference

### Success Criteria
- All 25+ audit issues are resolved
- No new TypeScript errors introduced
- All existing tests pass
- OpenAPI spec is in sync with backend
- ADRs are created for key decisions
- CONTEXT.md is updated with new terms
