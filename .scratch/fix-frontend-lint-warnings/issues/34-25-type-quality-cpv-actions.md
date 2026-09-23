# 34.25 — Type quality CPV actions

**What to build:** Type all quality CPV action functions in src/actions/quality-cpv.ts

**Blocked by:** Ticket 34 (parent)

**Status:** done

**Files:** src/actions/quality-cpv.ts

## Acceptance Criteria

- [ ] All quality CPV action functions have explicit return types
- [ ] All `as any` type assertions removed
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
