# 57 — Remove unused vars in hr components

**What to build:** Remove all unused imports and variables from `src/components/hr/` directory. This includes 14 unused variables across multiple HR-related component files.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Acceptance Criteria

- [ ] All unused imports removed from hr components
- [ ] All unused variables removed from hr components
- [ ] `tsc --noEmit` passes with no errors
- [ ] `pnpm lint` shows zero `@typescript-eslint/no-unused-vars` warnings in hr components
- [ ] No functional changes to hr features
