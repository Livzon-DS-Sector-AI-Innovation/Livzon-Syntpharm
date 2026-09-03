# 34.26 — Type quality inspection table actions

**What to build:** Type all quality inspection table action functions in src/actions/inspection-table.ts

**Blocked by:** Ticket 34 (parent)

**Status:** ready-for-agent

**Files:** src/actions/inspection-table.ts

## Acceptance Criteria

- [x] All quality inspection table action functions have explicit return types
- [x] All `as any` type assertions removed
- [x] Zero `@typescript-eslint/no-explicit-any` warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes on modified files
