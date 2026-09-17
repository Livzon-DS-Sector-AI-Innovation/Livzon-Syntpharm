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
- submitCheck: Promise<ApiResponse<SafetyCheck>>
- reviewCheck: Promise<ApiResponse<SafetyCheck>>
- deleteCheck: Promise<ApiResponse<null>>

All functions now properly await the server API response before casting to the specific ApiResponse type, eliminating the previous Promise casting issues.

## Bug Fix

Initially typed submitCheck and reviewCheck as returning `ApiResponse<unknown>`, which caused TypeScript errors (TS2345) in components that passed `response.data` to functions expecting `Partial<SafetyCheck>`. Fixed by changing the return types to `ApiResponse<SafetyCheck>`, which correctly reflects that the backend returns the updated SafetyCheck object after submit/review operations.

Commits:
- 865f67f: Initial typing of safety check actions
- 40aafa6: Correct return types for submitCheck and reviewCheck
