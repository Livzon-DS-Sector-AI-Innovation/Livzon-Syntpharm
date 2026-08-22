# 16 — Remove unused expressions (@typescript-eslint/no-unused-expressions)

**What to build:** Remove or refactor unused expressions to clean up code.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All unused expressions removed or refactored
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes (no @typescript-eslint/no-unused-expressions warnings)

## Summary

Fixed 1 @typescript-eslint/no-unused-expressions warning:
- OnboardingPrejobClient.tsx: converted unused expression to proper function call for fetchOnboardingEvaluationByEmployeeId

All unused expression warnings resolved.
