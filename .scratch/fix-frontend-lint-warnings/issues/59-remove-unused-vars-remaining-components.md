# 59 — Remove unused vars in remaining components (layout, quality, administration)

**What to build:** Remove all unused imports and variables from `src/components/layout/`, `src/components/quality/`, and `src/components/administration/` directories. This includes 5 unused variables across 4 files.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

## Acceptance Criteria

- [ ] All unused imports removed from remaining components
- [ ] All unused variables removed from remaining components
- [ ] `tsc --noEmit` passes with no errors
- [ ] `pnpm lint` shows zero `@typescript-eslint/no-unused-vars` warnings in these components
- [ ] No functional changes
