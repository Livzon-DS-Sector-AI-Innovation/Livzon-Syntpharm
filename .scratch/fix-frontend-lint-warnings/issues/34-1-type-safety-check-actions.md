# 34.1 — Type safety check actions

**What to build:** Type all safety check-related action functions (getChecks, createCheck, updateCheck, submitCheck, reviewCheck, deleteCheck, etc.)

**Blocked by:** Ticket 34 (parent)

**Status:** done

**Files:** src/actions/safety/index.ts (SafetyCheck section)

## Acceptance Criteria

- [x] All safety check action functions have explicit return types
- [x] All `as any` type assertions removed from check functions
- [x] Zero `@typescript-eslint/no-explicit-any` warnings in check functions
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes on modified files

## Implementation Summary

Added explicit return types to 7 safety check action functions:
- getChecks: Promise<ApiResponse<SafetyCheck[]>>
- getCheck: Promise<ApiResponse<SafetyCheck>>
- createCheck: Promise<ApiResponse<SafetyCheck>>
- updateCheck: Promise<ApiResponse<SafetyCheck>>
- submitCheck: Promise<ApiResponse<unknown>>
- reviewCheck: Promise<ApiResponse<unknown>>
- deleteCheck: Promise<ApiResponse<null>>

All functions now properly await the server API response before casting to the specific ApiResponse type, eliminating the previous Promise casting issues.

Commit: 865f67f
