# 34.26 — Type quality inspection table actions

**What to build:** Type all quality inspection table action functions in src/actions/inspection-table.ts

**Blocked by:** Ticket 34 (parent)

**Status:** ready-for-agent

**Files:** src/actions/inspection-table.ts

## Acceptance Criteria

- [ ] All quality inspection table action functions have explicit return types
- [ ] All `as any` type assertions removed
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
