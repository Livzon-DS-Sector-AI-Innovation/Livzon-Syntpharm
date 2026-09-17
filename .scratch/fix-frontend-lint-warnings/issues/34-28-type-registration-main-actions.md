# 34.28 — Type registration main actions

**What to build:** Type all registration main action functions in src/actions/registration.ts

**Blocked by:** Ticket 34 (parent)

**Status:** done

**Files:** src/actions/registration.ts

## Acceptance Criteria

- [x] All registration main action functions have explicit return types
- [x] All `as any` type assertions removed
- [x] Zero `@typescript-eslint/no-explicit-any` warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes on modified files
