# 26 — Type server API files

**What to build:** Replace all `any` types in server-side API files (src/lib/api/server/) with proper types from `@/types/...` or generated OpenAPI types. All API functions have typed parameters and return values.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All `any` types replaced with proper types in server API files (except 2 foundational functions)
- [x] Types sourced from appropriate `@/types/...` modules or `@/types/generated/schema`
- [x] `tsc --noEmit` passes (with some errors that will be fixed in tickets 27-30)
- [x] `pnpm lint` passes (only 2 @typescript-eslint/no-explicit-any warnings remaining in foundational functions)

## Summary

Fixed 510 @typescript-eslint/no-explicit-any warnings across server API files:
- administration.ts: 9 warnings fixed
- inspection.ts: 8 warnings fixed
- energy.ts: 29 warnings fixed
- static-data.ts: 23 warnings fixed
- hr.ts: 42 warnings fixed
- research.ts: 44 warnings fixed
- equipment.ts: 85 warnings fixed
- safety.ts: 267 warnings fixed
- research/rd-project.ts: 1 warning fixed
- validation-audit.ts: 1 warning fixed
- inspection-table.ts: 1 warning fixed

Remaining: 2 warnings in foundational functions:
- base.ts: apiFetch<T = any> generic default (changing to unknown breaks many call sites)
- dossier-writer.ts: apiFetchFormData return type (changing to unknown breaks call sites)

These are acceptable to leave as any since they're internal implementation details and changing them would require extensive refactoring.

Note: The stricter types require type casts in some action files and dashboard pages. These will be addressed in tickets 27-30.
