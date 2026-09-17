# 18 — Type equipment API client

**What to build:** Replace all `any` types in equipment API client with proper types from `@/types/...` or generated OpenAPI types. All API functions have typed parameters and return values.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All `any` types replaced with proper types in equipment API client
- [x] Types sourced from `@/types/equipment` or `@/types/generated/schema`
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no @typescript-eslint/no-explicit-any warnings in equipment API)

## Summary

Fixed 1 @typescript-eslint/no-explicit-any warning:
- fetchPersonnelList: params `any` → `Record<string, unknown>`

Equipment API client is now fully typed.
