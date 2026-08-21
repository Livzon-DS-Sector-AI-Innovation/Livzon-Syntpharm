# 53 — Remove unused vars in equipment components

**What to build:** Remove all unused imports and variables from `src/components/equipment/` directory. This includes 46 unused variables across multiple equipment-related component files.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Acceptance Criteria

- [ ] All unused imports removed from equipment components
- [ ] All unused variables removed from equipment components
- [ ] `tsc --noEmit` passes with no errors
- [ ] `pnpm lint` shows zero `@typescript-eslint/no-unused-vars` warnings in equipment components
- [ ] No functional changes to equipment features
