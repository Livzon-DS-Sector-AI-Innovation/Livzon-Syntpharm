# 30 — Type equipment components

**What to build:** Replace all `any` types in equipment components with proper types. Define interfaces where they don't exist. All props, parameters, and return values are properly typed.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All `any` types replaced with proper types in equipment components
- [x] Interfaces defined where needed
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no @typescript-eslint/no-explicit-any warnings in equipment components)

## Summary

Fixed all typecheck errors in equipment components by:
- Adding type assertions to API responses
- Wrapping unknown values with String() when needed
- Adding proper type casts for error handling

All typecheck errors are now resolved.
