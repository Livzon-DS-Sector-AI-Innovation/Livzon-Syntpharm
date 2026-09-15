# 60 — Remove unused vars in actions

**What to build:** Remove or prefix with `_` all unused variables/imports in src/actions/

**Status:** done

## Files fixed

- src/actions/hr.ts: Removed OnboardingRecord, TrainingLedgerRecord, FeishuSyncResult
- src/actions/safety/index.ts: Removed HazardIdentificationFormData, HazardIdentificationQueryParams, HazardIdentificationBatchCreateInput, HazardLedgerExportRequest

## Acceptance Criteria

- [x] All unused vars removed or prefixed with `_`
- [x] `pnpm lint` shows 0 `@typescript-eslint/no-unused-vars` warnings in src/actions/
- [x] `tsc --noEmit` passes
