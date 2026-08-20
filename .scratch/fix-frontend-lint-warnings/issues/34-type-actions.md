# 34 — Type actions

**What to build:** Replace all `any` types in action files (src/actions/) with proper types. All parameters and return values are properly typed.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] All `any` types replaced with proper types in action files
- [ ] `tsc --noEmit` passes
- [ ] `pnpm lint` passes (no @typescript-eslint/no-explicit-any warnings in actions)
