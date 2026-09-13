# 34.31 — Type deviation actions

**What to build:** Type all deviation action functions in src/actions/deviation.ts

**Blocked by:** Ticket 34 (parent)

**Status:** done

**Files:** src/actions/deviation.ts

## Acceptance Criteria

- [x] All deviation action functions have explicit return types
- [x] All `as any` type assertions removed
- [x] Zero `@typescript-eslint/no-explicit-any` warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes on modified files
