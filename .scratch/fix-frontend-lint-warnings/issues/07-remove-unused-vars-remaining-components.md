# 7 — Remove unused vars in remaining components (layout, quality, administration)

**What to build:** Remove all unused imports and variables from `src/components/layout/`, `src/components/quality/`, and `src/components/administration/` directories. This includes 5 unused variables across 4 files.

**Blocked by:** None — can start immediately

**Status:** done

**Result:** Already completed in commit 89b591c2. Removed 5 unused vars across 4 files:
- `administration/RegulationClient.tsx` (total)
- `layout/Sidebar.tsx` (currentUser)
- `layout/TopNav.tsx` (visibleMenus)
- `quality/ReportEditor.tsx` (Tag, Upload)

**Verification:**
- [x] All unused imports removed from remaining components
- [x] All unused variables removed from remaining components
- [x] `tsc --noEmit` passes with no errors
- [x] `pnpm lint` shows zero `@typescript-eslint/no-unused-vars` warnings in these components
- [x] No functional changes
