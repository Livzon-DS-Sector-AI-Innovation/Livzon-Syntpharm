# 34.24 — Type quality main actions

**What to build:** Type all quality main action functions in src/actions/quality.ts

**Blocked by:** Ticket 34 (parent)

**Status:** done

**Files:** src/actions/quality.ts

## Acceptance Criteria

- [ ] All quality main action functions have explicit return types
- [ ] All `as any` type assertions removed
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
