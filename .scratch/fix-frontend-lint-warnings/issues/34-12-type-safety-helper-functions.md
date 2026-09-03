# 34.12 — Type safety helper functions

**What to build:** Type safety helper functions in src/actions/safety/helpers.ts

**Blocked by:** Ticket 34 (parent)

**Status:** done

**Files:** src/actions/safety/helpers.ts

## Acceptance Criteria

- [ ] All helper functions have explicit return types
- [ ] All `as any` type assertions removed
- [ ] Zero `@typescript-eslint/no-explicit-any` warnings
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes on modified files
