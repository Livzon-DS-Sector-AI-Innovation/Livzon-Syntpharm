# 34.36 — Type administration actions

**What to build:** Type all administration action functions in src/actions/administration.ts

**Blocked by:** Ticket 34 (parent)

**Status:** done

**Files:** src/actions/administration.ts

## Acceptance Criteria

- [x] All administration action functions have explicit return types
- [x] All `as any` type assertions removed
- [x] Zero `@typescript-eslint/no-explicit-any` warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes on modified files
