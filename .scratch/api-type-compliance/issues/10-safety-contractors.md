# 10 — Safety contractors: response models + frontend types

**What to build:** Frontend can use generated types for contractor CRUD, work records, and training APIs. Backend contractor endpoints switch to specific response wrappers.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Response wrapper schemas created: `ContractorApiResponse`, `ContractorListApiResponse`, `ContractorWorkRecordApiResponse`, `ContractorWorkRecordListApiResponse`
- [ ] All contractor endpoints updated to use specific response models
- [ ] Backend OpenAPI spec exported and includes contractor response schemas
- [ ] Frontend types regenerated from updated spec
- [ ] Frontend contractor API calls updated to use generated types (replace `safeApiFetch<unknown>` with concrete types)
- [ ] TypeScript compilation passes
- [ ] Runtime API responses match generated types (spot-check 2-3 contractor endpoints)
