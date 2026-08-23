# 34.27 — Type quality doc-check actions

**What to build:** Type all quality doc-check action functions in src/actions/doc-check.ts

**Blocked by:** Ticket 34 (parent)

**Status:** ready-for-agent

**Files:** src/actions/doc-check.ts

## Acceptance Criteria

- [ ] All quality doc-check action functions have explicit return types
- [ ] All `as any` type assertions removed
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
