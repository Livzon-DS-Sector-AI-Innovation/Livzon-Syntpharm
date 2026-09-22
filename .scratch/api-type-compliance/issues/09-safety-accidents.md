# 09 — Safety accidents: response models + frontend types

**What to build:** Frontend can use generated types for accident CRUD, investigation, and resolution APIs. Backend accident endpoints switch to specific response wrappers.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Response wrapper schemas created: `AccidentApiResponse`, `AccidentListApiResponse`
- [ ] All accident endpoints updated to use specific response models
- [ ] Backend OpenAPI spec exported and includes accident response schemas
- [ ] Frontend types regenerated from updated spec
- [ ] Frontend accident API calls updated to use generated types (replace `safeApiFetch<unknown>` with concrete types)
- [ ] TypeScript compilation passes
- [ ] Runtime API responses match generated types (spot-check 2-3 accident endpoints)
