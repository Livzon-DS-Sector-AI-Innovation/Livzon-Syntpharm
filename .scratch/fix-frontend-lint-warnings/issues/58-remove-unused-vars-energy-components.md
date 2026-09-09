# 58 — Remove unused vars in energy components

**What to build:** Remove all unused imports and variables from `src/components/energy/` directory. This includes 10 unused variables across multiple energy-related component files.

**Blocked by:** None — can start immediately

**Status:** done

## Acceptance Criteria

- [x] All unused imports removed from energy components
- [x] All unused variables removed from energy components
- [x] `tsc --noEmit` passes with no errors
- [x] `pnpm lint` shows zero `@typescript-eslint/no-unused-vars` warnings in energy components
- [x] No functional changes to energy features

## Changes Made

### AlertsPageClient.tsx
- Line 14: Renamed unused destructured variable `alertConfigDrawerOpen` to `_alertConfigDrawerOpen`

### CollectLogDetailDrawer.tsx
- Line 3: Removed unused import `useState`
- Line 12: Removed unused import `CollectLogDetail`
- Line 166: Renamed unused variable `message` to `_message`

### MonthlyRecordTable.tsx
- Line 124: Renamed unused function `loadSummary` to `_loadSummary`
- Line 138: Renamed unused function `loadWorkshops` to `_loadWorkshops`

## Verification
- All unused vars warnings resolved in energy components
- TypeScript compilation passes with no errors
- No functional changes made
