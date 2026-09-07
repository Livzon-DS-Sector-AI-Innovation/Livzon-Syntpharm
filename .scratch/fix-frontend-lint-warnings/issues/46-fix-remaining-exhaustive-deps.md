# 46 — Fix remaining exhaustive-deps warnings (31 warnings in 23 files)

**What to build:** Fix the remaining 31 react-hooks/exhaustive-deps warnings across the codebase. These warnings occur when React hooks (useEffect, useCallback, useMemo) have missing dependencies in their dependency arrays.

**Status:** todo

## Files with warnings:

### Quality module (6 files, 8 warnings):
- `quality/deviation-automation/preview/[id]/page.tsx` - 2 warnings
- `quality/deviation-automation/templates/page.tsx` - 1 warning
- `quality/deviation-flow/create/page.tsx` - 1 warning
- `quality/deviation-flow/progress/page.tsx` - 1 warning
- `quality/instrument/list/edit/page.tsx` - 1 warning
- `quality/deviation-flow/settings/page.tsx` - 2 warnings

### Registration module (1 file, 1 warning):
- `registration/ledger/page.tsx` - 1 warning

### Energy module (1 file, 1 warning):
- `components/energy/DeviceDrawer.tsx` - 1 warning

### HR module (2 files, 2 warnings):
- `components/hr/TrainingSelectClient.tsx` - 1 warning
- `components/hr/TrainingSessionDetailModal.tsx` - 1 warning

### Production module (3 files, 3 warnings):
- `components/production/AnnualReviewTab.tsx` - 1 warning
- `components/production/WorkshopRankingTrend.tsx` - 1 warning
- `components/production/pressure/PressureManualInputPageClient.tsx` - 1 warning

### Research module (1 file, 1 warning):
- `components/research/StageModuleLayout.tsx` - 1 warning

### Safety module (9 files, 15 warnings):
- `components/safety/HazardLedgerPage.tsx` - 1 warning
- `components/safety/HazardLedgerPanel.tsx` - 3 warnings
- `components/safety/HazardSelectModal.tsx` - 1 warning
- `components/safety/SopContentEditor.tsx` - 1 warning
- `components/safety/SpecialOpsLedger.tsx` - 1 warning
- `components/safety/SpecialOpsManagement.tsx` - 1 warning
- `components/safety/WorkflowListPanel.tsx` - 1 warning
- `components/safety/hazard-identification/HazardIdentificationDetailPageClient.tsx` - 1 warning
- `components/safety/hazard/HazardDetailPageClient.tsx` - 1 warning
- `components/safety/regulation/SafetyRegulationPageClient.tsx` - 2 warnings

## Common fix patterns:
1. Wrap functions used in useEffect/useCallback with `useCallback` and add proper dependencies
2. Add missing dependencies to dependency arrays
3. Reorder function declarations to avoid "used before declaration" errors
4. Import `useCallback` from React where missing

## Acceptance criteria:
- [ ] `pnpm lint` shows 0 exhaustive-deps warnings
- [ ] `tsc --noEmit` passes
- [ ] No runtime errors introduced
- [ ] All hooks follow React's rules of hooks
