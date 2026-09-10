# 60 — Remove unused vars in actions

**What to build:** Remove or prefix with `_` all unused variables/imports in src/actions/

**Status:** ready-for-agent

## Files to fix

- src/actions/hr.ts: OnboardingRecord, TrainingLedgerRecord, FeishuSyncResult
- src/actions/safety/index.ts: KnowledgeCardContent, HazardIdentificationFormData, HazardIdentificationQueryParams, HazardIdentificationBatchCreateInput, HazardLedgerExportRequest

## Acceptance Criteria

- [ ] All unused vars removed or prefixed with `_`
- [ ] `pnpm lint` shows 0 `@typescript-eslint/no-unused-vars` warnings in src/actions/
- [ ] `tsc --noEmit` passes
