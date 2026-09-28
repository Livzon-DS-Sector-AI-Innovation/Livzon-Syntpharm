# API Type Compliance Fix

**Status:** ready-for-agent  
**Created:** 2026-09-18  
**Source:** AI Audit Category 10 (Frontend API and generated types)

## Problem Statement

Frontend API calls use hand-written TypeScript types or `unknown` instead of types generated from the backend OpenAPI spec. This violates AGENTS.md rule "API 类型来源/必须从 generated schema 导入" and causes:

1. **Type drift**: Frontend types can diverge from backend contracts
2. **Lost type safety**: Using `unknown` or hand-written types defeats TypeScript's compile-time checking
3. **Manual maintenance**: Developers must manually update types when backend changes
4. **Audit violations**: 3 confirmed findings in AI audit

Root cause: Backend quality and safety modules use generic `response_model=ApiResponse` instead of specific response models, preventing OpenAPI spec generation from producing usable types.

## Solution

1. **Regenerate frontend types** from updated backend OpenAPI spec (energy module already correct)
2. **Fix backend response models** for quality and safety modules to use specific response types
3. **Update frontend API calls** to use generated types instead of hand-written or `unknown`
4. **Clean up type definition files** to remove redundant hand-written API types

## User Stories

1. As a frontend developer, I want API response types to be auto-generated from the backend spec, so that I don't have to manually maintain type definitions
2. As a frontend developer, I want compile-time type checking for API responses, so that I catch contract mismatches before runtime
3. As a backend developer, I want to know exactly what response shape each endpoint returns, so that I can maintain API contracts correctly
4. As a code reviewer, I want to verify API type compliance automatically, so that I don't have to manually check each API call
5. As an AI auditor, I want frontend code to follow the "API types from generated schema" rule, so that audit findings are resolved
6. As a developer working on energy module, I want to use generated types for `EnergyDeviceConfig`, `AlertRule`, `AlertRecord`, etc., so that my code matches the backend contract
7. As a developer working on quality module, I want to use generated types for deviation and CAPA APIs, so that I have type safety
8. As a developer working on safety module, I want to use generated types for hazard and check APIs, so that I have type safety
9. As a developer, I want the OpenAPI spec to include all response schemas, so that frontend types can be fully generated
10. As a developer, I want to know which types are backend spec gaps (not yet in OpenAPI), so that I can track what needs backend work
11. As a developer, I want UI-specific types (form state, component props) to remain hand-written, so that I can model frontend-only concerns
12. As a developer, I want the `ApiResponse` wrapper pattern to be handled transparently, so that I don't have to deal with it in every API call
13. As a developer, I want to run `pnpm generate:api` to regenerate types, so that I can quickly sync with backend changes
14. As a CI system, I want to verify that frontend types are up-to-date with backend spec, so that type drift is caught early
15. As a developer, I want to see which backend endpoints still use generic `ApiResponse`, so that I can prioritize migration work
16. As a developer, I want deviation list endpoints to return typed responses, so that I can iterate over deviations with type safety
17. As a developer, I want deviation detail endpoints to return typed responses, so that I can access deviation fields without casting
18. As a developer, I want CAPA endpoints to return typed responses, so that I can work with CAPA data safely
19. As a developer, I want inspection standard endpoints to return typed responses, so that I can work with standards safely
20. As a developer, I want safety check endpoints to return typed responses, so that I can work with checks safely
21. As a developer, I want hazard identification endpoints to return typed responses, so that I can work with hazards safely
22. As a developer, I want accident endpoints to return typed responses, so that I can work with accidents safely
23. As a developer, I want contractor endpoints to return typed responses, so that I can work with contractors safely
24. As a developer, I want training endpoints to return typed responses, so that I can work with training data safely
25. As a developer, I want the migration to be incremental, so that I can fix one module at a time without breaking existing code
26. As a developer, I want to see examples of correct response model usage, so that I can follow the pattern when adding new endpoints
27. As a developer, I want to understand the relationship between `build_response()`, `ApiResponse`, and specific response models, so that I can choose the right pattern
28. As a developer, I want energy overview data to be in the backend spec, so that I can use generated types for it
29. As a developer, I want collect log types to be in the backend spec, so that I can use generated types for them
30. As a developer, I want energy statistics types to be in the backend spec, so that I can use generated types for them
31. As a developer, I want to know which frontend types have no backend equivalent, so that I can document them as intentional gaps
32. As a developer, I want the type alias pattern (`export type X = components['schemas']['XResponse']`) to be used consistently, so that I can migrate gradually
33. As a developer, I want to preserve backward compatibility during migration, so that I don't break existing frontend code
34. As a developer, I want to test that API responses match generated types at runtime, so that I can catch spec drift
35. As a developer, I want TypeScript compilation to pass after migration, so that I know the types are correct
36. As a developer, I want to verify OpenAPI spec includes new response schemas, so that I know backend changes are complete
37. As a developer, I want to verify frontend types include new schemas, so that I know regeneration worked
38. As a developer, I want to see the before/after diff for API calls, so that I can understand the migration pattern
39. As a developer, I want to know the exact commands to regenerate types, so that I can do it myself
40. As a developer, I want to understand why `response_model=ApiResponse` is prohibited, so that I can explain it to others
41. As a developer, I want to see the AGENTS.md rule that prohibits generic response models, so that I can reference it
42. As a developer, I want to know which files were changed in the migration, so that I can review them
43. As a developer, I want to know which tests to run to verify the migration, so that I can ensure nothing broke
44. As a developer, I want to know how to add new endpoints with correct response models, so that I don't reintroduce the problem
45. As a developer, I want to see a checklist of endpoints that need migration, so that I can track progress
46. As a developer, I want to prioritize migration by usage frequency, so that I fix the most impactful endpoints first
47. As a developer, I want to understand the difference between response models and response wrappers, so that I can model APIs correctly
48. As a developer, I want to see how energy module implements correct response models, so that I can follow the same pattern
49. As a developer, I want to know if there are any exceptions to the "no generic ApiResponse" rule, so that I can handle edge cases
50. As a developer, I want to know how file downloads and streaming responses should be typed, so that I can handle non-JSON responses

## Implementation Decisions

### Backend Response Model Pattern

**Decision**: Follow energy module pattern for response models.

Each endpoint uses a specific response wrapper:
- Single item: `XxxApiResponse` with `data: XxxResponse`
- List: `XxxListApiResponse` with `data: list[XxxResponse]` and optional `meta`
- Statistics: `XxxStatisticsApiResponse` with `data: XxxStatistics`

The wrapper includes `code`, `message`, and `data` fields. The `data` field contains the actual business data.

**Rationale**: This pattern is already used in energy module and generates proper OpenAPI schemas. It allows frontend to use generated types while maintaining the standard `{code, message, data}` response format.

### Quality Module Migration

**Decision**: Create response wrappers in `deviation_schemas.py` and `schemas.py`.

- Deviation endpoints: `DeviationApiResponse`, `DeviationListApiResponse`, `DeviationStatisticsApiResponse`
- Investigation endpoints: `InvestigationApiResponse`, `InvestigationListApiResponse`
- Correction endpoints: `CorrectionApiResponse`
- Closing endpoints: `ClosingApiResponse`
- AI analysis endpoints: `AIAnalysisApiResponse`
- Inspection standard endpoints: `InspectionStandardApiResponse`, `InspectionStandardListApiResponse`
- CAPA endpoints: `CapaApiResponse`, `CapaListApiResponse`

Update all `response_model=ApiResponse` to use specific wrappers.

**Rationale**: Keeps response schemas co-located with request schemas in the same file. Makes it easy to find and update.

### Safety Module Migration

**Decision**: Create response wrappers in `schemas/` directory.

- Check endpoints: `SafetyCheckApiResponse`, `SafetyCheckListApiResponse`
- Hazard endpoints: `HazardApiResponse`, `HazardListApiResponse`
- Accident endpoints: `AccidentApiResponse`, `AccidentListApiResponse`
- Contractor endpoints: `ContractorApiResponse`, `ContractorListApiResponse`
- Training endpoints: `TrainingApiResponse`, `TrainingListApiResponse`

Update all `response_model=ApiResponse` to use specific wrappers.

**Rationale**: Safety module has multiple API files, so schemas are organized in a directory. Each sub-module gets its own response wrappers.

### Frontend Type Regeneration

**Decision**: Run `pnpm generate:api` after backend changes.

This regenerates `src/types/generated/schema.ts` from the updated OpenAPI spec. The generated types include all response wrappers and their nested data types.

**Rationale**: This is the standard workflow documented in AGENTS.md. It ensures frontend types always match backend spec.

### Frontend Type Alias Pattern

**Decision**: Use type aliases to bridge generated types and existing code.

Example:
```typescript
export type EnergyDeviceConfig = components['schemas']['EnergyDeviceConfigResponse']
```

This allows gradual migration without breaking all imports at once.

**Rationale**: Preserves backward compatibility. Allows incremental migration. Makes it clear which types come from generated schema.

### Backend Spec Gaps

**Decision**: Document types that are NOT in backend spec as intentional gaps.

Types like `EnergyOverviewData`, `EnergyData`, `EnergyStatistics`, `CollectLog` are not in backend OpenAPI spec. These indicate backend endpoints that need proper response models.

**Rationale**: Makes it clear which types need backend work vs. which are just frontend UI types.

### UI-Specific Types

**Decision**: Keep UI-specific types (form state, component props) hand-written.

These types are not API contracts and don't need to be in OpenAPI spec.

**Rationale**: AGENTS.md rule only applies to API contract types. UI types are frontend-only concerns.

### ApiResponse Wrapper Handling

**Decision**: Frontend API helpers (`apiGet`, `safeApiFetch`) handle the `{code, message, data}` wrapper transparently.

The generated types include the wrapper, but API helpers extract the `data` field.

**Rationale**: Developers work with business data, not the wrapper. The wrapper is an implementation detail.

## Testing Decisions

### What Makes a Good Test

- Test external behavior (API response shape), not implementation details
- Verify TypeScript compilation passes
- Verify runtime API responses match generated types
- Verify OpenAPI spec includes all response schemas

### Modules to Test

1. **Backend OpenAPI spec generation**: Verify all endpoints have specific response models
2. **Frontend type generation**: Verify `pnpm generate:api` produces correct types
3. **Frontend API calls**: Verify API calls use generated types
4. **TypeScript compilation**: Verify `pnpm typecheck` passes
5. **Runtime validation**: Test a few API endpoints in browser to ensure response shapes match

### Prior Art

- Energy module already uses this pattern successfully
- AGENTS.md documents the rule and workflow
- `scripts/ci/export_openapi.py` exports backend spec
- `scripts/generate-api.mjs` generates frontend types

## Out of Scope

1. **Backend spec gaps**: Types not in backend spec (e.g., `EnergyOverviewData`) will be addressed in separate specs
2. **UI type refactoring**: Hand-written UI types (form state, component props) are out of scope
3. **API behavior changes**: This spec only changes type annotations, not API behavior
4. **New endpoints**: New endpoints should follow the correct pattern, but existing endpoints are the focus
5. **CI enforcement**: Automated CI checks for type compliance are out of scope (may be added later)
6. **Documentation updates**: AGENTS.md already documents the rule; no documentation changes needed
7. **Migration of other modules**: Only energy, quality, and safety modules are in scope

## Further Notes

### Migration Order

1. **Phase 1**: Regenerate energy frontend types (backend already correct)
2. **Phase 2**: Fix quality backend response models, then regenerate frontend types
3. **Phase 3**: Fix safety backend response models, then regenerate frontend types
4. **Phase 4**: Clean up frontend type definition files

### Commands to Run

```bash
# Export backend OpenAPI spec
cd backend && .venv/bin/python scripts/ci/export_openapi.py

# Copy spec to frontend
cp backend/openapi.json frontend/src/types/generated/openapi.json

# Regenerate frontend types
cd frontend && pnpm generate:api

# Verify TypeScript compilation
cd frontend && pnpm typecheck
```

### Verification Checklist

- [ ] Backend OpenAPI spec includes all response schemas
- [ ] Frontend types include all generated schemas
- [ ] Frontend API calls use generated types
- [ ] TypeScript compilation passes
- [ ] Runtime API responses match generated types
- [ ] No `response_model=ApiResponse` in quality module
- [ ] No `response_model=ApiResponse` in safety module
- [ ] No `safeApiFetch<unknown>` in safety.ts
- [ ] No hand-written API types in energy.ts (except backend gaps)
- [ ] No hand-written API types in quality.ts (except backend gaps)

### Risk Mitigation

- **Incremental migration**: Fix one module at a time to minimize risk
- **Backward compatibility**: Use type aliases to preserve existing imports
- **Testing**: Verify TypeScript compilation and runtime behavior after each phase
- **Rollback**: Git commits after each phase allow easy rollback if needed
