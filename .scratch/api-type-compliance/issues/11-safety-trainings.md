# 11 — Safety trainings: response models + frontend types

**What to build:** Frontend can use generated types for training CRUD and training record APIs. Backend training endpoints switch to specific response wrappers.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Response wrapper schemas created: `SafetyTrainingApiResponse`, `SafetyTrainingListApiResponse`, `TrainingRecordApiResponse`, `TrainingRecordListApiResponse`
- [ ] All training endpoints updated to use specific response models
- [ ] Backend OpenAPI spec exported and includes training response schemas
- [ ] Frontend types regenerated from updated spec
- [ ] Frontend training API calls updated to use generated types (replace `safeApiFetch<unknown>` with concrete types)
- [ ] TypeScript compilation passes
- [ ] Runtime API responses match generated types (spot-check 2-3 training endpoints)
