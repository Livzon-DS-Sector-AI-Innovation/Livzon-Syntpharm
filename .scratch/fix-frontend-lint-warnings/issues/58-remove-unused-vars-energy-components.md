# 58 — Remove unused vars in energy components

**What to build:** Remove all unused imports and variables from `src/components/energy/` directory. This includes 10 unused variables across multiple energy-related component files.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Acceptance Criteria

- [ ] All unused imports removed from energy components
- [ ] All unused variables removed from energy components
- [ ] `tsc --noEmit` passes with no errors
- [ ] `pnpm lint` shows zero `@typescript-eslint/no-unused-vars` warnings in energy components
- [ ] No functional changes to energy features
