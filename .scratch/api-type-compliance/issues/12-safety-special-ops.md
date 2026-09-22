# 12 — Safety special operations: response models + frontend types

**What to build:** Frontend can use generated types for special operation permits, personnel, and reports APIs. Backend special operation endpoints switch to specific response wrappers.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Response wrapper schemas created: `SpecialOperationPermitApiResponse`, `SpecialOperationPermitListApiResponse`, `SpecialOperationPersonnelApiResponse`, `SpecialOperationPersonnelListApiResponse`, `SpecialOperationReportApiResponse`, `SpecialOperationReportListApiResponse`
- [ ] All special operation endpoints updated to use specific response models
- [ ] Backend OpenAPI spec exported and includes special operation response schemas
- [ ] Frontend types regenerated from updated spec
- [ ] Frontend special operation API calls updated to use generated types (replace `safeApiFetch<unknown>` with concrete types)
- [ ] TypeScript compilation passes
- [ ] Runtime API responses match generated types (spot-check 2-3 special operation endpoints)
