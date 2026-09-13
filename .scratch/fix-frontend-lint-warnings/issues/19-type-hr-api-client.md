# 19 — Type hr API client

**What to build:** Replace all `any` types in hr API client with proper types from `@/types/...` or generated OpenAPI types. All API functions have typed parameters and return values.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All `any` types replaced with proper types in hr API client
- [x] Types sourced from `@/types/hr` or `@/types/generated/schema`
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no @typescript-eslint/no-explicit-any warnings in hr API)

## Summary

Fixed 2 @typescript-eslint/no-explicit-any warnings:
- fetchCandidates: params `Record<string, any>` → `Record<string, unknown>`, return `data: any[]` → `Candidate[]`
- Added Candidate type import

HR API client is now fully typed.
