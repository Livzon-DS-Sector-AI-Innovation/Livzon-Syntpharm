# 52 — Remove unused vars in safety components

**What to build:** Remove all unused imports and variables from `src/components/safety/` directory. This includes 98 unused variables across multiple safety-related component files.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Acceptance Criteria

- [ ] All unused imports removed from safety components
- [ ] All unused variables removed from safety components
- [ ] `tsc --noEmit` passes with no errors
- [ ] `pnpm lint` shows zero `@typescript-eslint/no-unused-vars` warnings in safety components
- [ ] No functional changes to safety features
