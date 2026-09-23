# 34.39 — Type small utility actions

**What to build:** Type all small utility action functions across multiple files: src/actions/admin.ts, src/actions/environment.ts, src/actions/identity.ts, src/actions/pressure.ts, src/actions/ai-parse.ts, src/actions/instrument.ts, src/actions/procurement.ts, and src/actions/users.ts

**Blocked by:** Ticket 34 (parent)

**Status:** done

**Files:** src/actions/admin.ts, src/actions/environment.ts, src/actions/identity.ts, src/actions/pressure.ts, src/actions/ai-parse.ts, src/actions/instrument.ts, src/actions/procurement.ts, src/actions/users.ts

## Acceptance Criteria

- [x] All small utility action functions have explicit return types
- [x] All `as any` type assertions removed
- [x] Zero `@typescript-eslint/no-explicit-any` warnings
- [x] `tsc --noEmit` passes
- [x] `pnpm lint` passes on modified files
