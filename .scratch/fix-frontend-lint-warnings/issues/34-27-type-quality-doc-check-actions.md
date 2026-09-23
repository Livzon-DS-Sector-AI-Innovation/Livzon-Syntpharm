# 34.27 — Type quality doc-check actions

**What to build:** Type all quality doc-check action functions in src/actions/doc-check.ts

**Blocked by:** Ticket 34 (parent)

**Status:** done

**Files:** src/actions/doc-check.ts

## Acceptance Criteria

- [x] All quality doc-check action functions have explicit return types
- [x] All `as any` type assertions removed
- [x] Zero `@typescript-eslint/no-explicit-any` warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes on modified files
