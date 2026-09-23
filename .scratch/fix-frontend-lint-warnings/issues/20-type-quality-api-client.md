# 20 — Type quality API client

**What to build:** Replace all `any` types in quality API client with proper types from `@/types/...` or generated OpenAPI types. All API functions have typed parameters and return values.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All `any` types replaced with proper types in quality API client
- [x] Types sourced from `@/types/quality` or `@/types/generated/schema`
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no @typescript-eslint/no-explicit-any warnings in quality API)

## Summary

Fixed 7 @typescript-eslint/no-explicit-any warnings:
- fetchCapa: return `any` → `CapaDetail`
- fetchCapas: `apiFetchPaginated<any>` → `apiFetchPaginated<CapaListItem>`
- fetchDeviations: `apiFetchPaginated<any>` → `apiFetchPaginated<DeviationListItem>`
- fetchDeviation: return `any` → `DeviationDetail`
- fetchDepartmentContacts: `apiFetchPaginated<any>` → `apiFetchPaginated<DepartmentContact>`
- Added CapaDetail, DeviationDetail, DepartmentContact, CapaListItem, DeviationListItem imports

Quality API client is now fully typed.
