# 34.33 — Type static-data actions

**What to build:** Type all static-data action functions in src/actions/static-data.ts

**Blocked by:** Ticket 34 (parent)

**Status:** done

**Files:** src/actions/static-data.ts

## Acceptance Criteria

- [x] All static-data action functions have explicit return types
- [x] All `as any` type assertions removed
- [x] Zero `@typescript-eslint/no-explicit-any` warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes on modified files
